import numpy as np
import torch
from torch.optim import SGD
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm
from utils import reset_parameters, ListLogger

class Trainer():
    """General class for training models.

    The __init__ method takes in the model and the training dataset, as well as
    any transforms to apply to the dataset.

    Args:
        model: PyTorch neural network module
        dataset: Training dataset
        transform: Transforms to apply to the input dataset
        device: Device to run calculations on

    Attributes:
        train_split: Training split (80% of dataset)
        val_split: Validation split (20% of dataset)
        log: Dictionary of metrics to log while training
    """
    def __init__(self, dataset, test_dataset, transform=None, device='cpu'):
        self.dataset = dataset
        self.test_dataset = test_dataset
        self.transform = transform
        self.device = device
        self.logger = ListLogger()
        self.resplit()

    def reset_logger(self):
        self.logger = ListLogger()

    def resplit(self):
        """Regenerates dataset splits."""
        # TODO: implement balanced splitting
        self.train_split, self.val_split = random_split(self.dataset, [0.8, 0.2])

    def train(self, model, optimizer, criterion, epochs=1, batch_size=1, leave=False):
        """Training loop using the provided optimizer, criterion, and training
        parameters.
        """
        train_loader = DataLoader(self.train_split, batch_size=batch_size, shuffle=True)
        model = model.to(self.device)
        model.train()
        for epoch in tqdm(range(1, epochs+1), leave=leave):
            for X, y in train_loader:
                X, y = X.to(self.device), y.to(self.device)
                if self.transform is not None:
                    X = self.transform(X)
                optimizer.zero_grad()
                logits = model(X)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()
            train_loss, train_acc, train_closs, train_clacc = self.eval(model, self.train_split, criterion)
            val_loss, val_acc, val_closs, val_clacc = self.eval(model, self.val_split, criterion)

            self.logger.log('epochs', v=epoch)
            self.logger.log('train_loss', v=train_loss)
            self.logger.log('train_acc', v=train_acc)
            self.logger.log('val_loss', v=val_loss)
            self.logger.log('val_acc', v=val_acc)
            for c in train_closs.keys():
                self.logger.log('train_class_loss', c, v=train_closs[c])
                self.logger.log('train_class_acc', c, v=train_clacc[c])
                self.logger.log('val_class_loss', c, v=val_closs[c])
                self.logger.log('val_class_acc', c, v=val_clacc[c])
        test_loss, test_acc, test_closs, test_clacc = self.eval(model, self.test_dataset, criterion)
        self.logger.log('test_loss', v=test_loss)
        self.logger.log('test_acc', v=test_acc)
        for c in test_closs.keys():
            self.logger.log('test_class_loss', c, v=test_closs[c])
            self.logger.log('test_class_acc', c, v=test_clacc[c])
        return self.logger, model

    def eval(self, model, dataset, criterion):
        """Evaluation loop using the provided criterion.
        """
        loader = DataLoader(dataset, batch_size=len(dataset))
        model = model.to(self.device)
        model.eval()
        with torch.inference_mode():
            for X, y in loader:
                X, y = X.to(self.device), y.to(self.device)
                logits = model(X)
                loss = criterion(logits, y)
                y_hat = torch.argmax(logits, dim=1)
                y_ = (y_hat == y)
                acc = torch.sum(y_) / len(y)
                # Class-specific logging
                class_loss, class_acc = {}, {}
                for c in torch.unique(y):
                    c = c.item()
                    cargs = torch.argwhere(y == c).squeeze() # Squeeze shape [c, 1] to [c] for indexing
                    class_loss[c] = criterion(logits[cargs, :], y[cargs])
                    class_acc[c] = torch.sum(y_hat[cargs] == y[cargs]) / len(y[cargs])
        return loss, acc, class_loss, class_acc
