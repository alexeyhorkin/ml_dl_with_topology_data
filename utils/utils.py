'''All useful utils here.'''

import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from os.path import join as p_join

import torch
import torch.nn.functional as F


#########################################
##      DATA PROCESSING FUNCTIONS      ##
#########################################

def create_dataset(folders, verbose=False, feature_nums=16):
    X_merged, Y_merged = [], []
    for folder_path in tqdm(folders):
        X_path = p_join('..', 'data_2', folder_path, '2nd_exp_Input.txt')
        Y_path_down = p_join('..', 'data_2', folder_path, '2nd_exp_Topology_down.txt')
        Y_path_up = p_join('..', 'data_2', folder_path, '2nd_exp_Topology_up.txt')
        params_path = p_join('..', 'data_2', folder_path, '2nd_exp_Parameters.txt')

        X = select_n_center_features(pd.read_csv(X_path).values, feature_nums)
        Y_down = pd.read_csv(Y_path_down).values
        Y_up = pd.read_csv(Y_path_up).values
        Y = np.array([map_classes(Y_up[i], Y_down[i]) for i in range(Y_up.shape[0])])

        X_merged.append(X)
        Y_merged.append(Y)

    # Merge and shuffle it!
    X, Y = np.concatenate(X_merged, axis=0), np.concatenate(Y_merged, axis=0)
    indexes_for_shuffle = np.random.permutation(np.arange(X.shape[0]))
    X = X[indexes_for_shuffle]
    Y = Y[indexes_for_shuffle]
    if verbose:
        print('Dataset cteated!')
    return X, Y

def normalize_data(X):
    mean = X.mean(0)
    std = X.std(0)
    return (X - mean) / std


def select_n_center_features(data: np.ndarray, n_features: int, verbose: bool = False) -> np.ndarray:
    from copy import deepcopy

    total_components = data.shape[1]
    start = int((total_components - n_features)/2)
    res = deepcopy(data)[:, start: start + n_features]
    if verbose:
        print(f'Selected features from indexes:  [{start}, {start + n_features})')
    return res

def map_classes(i, j):
    if i == 0 and j == 0:
        return 0
    elif i == 0 and j == 1:
        return 1
    elif i == 1 and j == 0:
        return 2
    elif i == 1 and j == 1:
        return 3



#########################################
## TRAINING AND TESTING FUNCTIONS (DL) ##
#########################################

def train_epoch(net, optimizer, dataloader, criterion, device):
    """Perform one traing epoch"""
    running_loss = 0.0
    net.train(True)
    for X, y in tqdm(dataloader):
        X = X.to(device)
        y = y.to(device).long()
        optimizer.zero_grad()
        y_hat = net(X)
        loss = criterion(y_hat, y)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    
    return running_loss / len(dataloader)

def test_model(net, dataloader, device):
    """Return accuracy"""
    correct, count = 0, 0
    net.eval()
    with torch.no_grad():
        for X, y in tqdm(dataloader):
            X = X.to(device)
            y = y.to(device).long()
            logits = net(X)
            _, y_hat = torch.max(logits, dim=1)
            correct += (y_hat == y).sum().item()
            count += y_hat.shape[0]
    
    return 100 * correct / count


def run_training(net, optimizer, config, train_loader, test_loader=None):
    ### Get hyperparams from config
    epochs = config.get('ephs', 10)
    device = config.get('device', 'cpu')
    criterion = config.get('criterion', F.cross_entropy)
    ckpt_save_folder = config.get('ckpt_save_folder', './ckpts')
    save_ckpts = config.get('save_ckpts', False)
    
    ### Define local constants
    best_score = -np.inf
    
    if not os.path.exists(ckpt_save_folder):
        os.makedirs(ckpt_save_folder)
    
    ### Start trainig
    for eph in range(1, epochs + 1):
            mean_loss = train_epoch(net, optimizer, train_loader, criterion, device)
            print(f"Epoch: {eph}/{epochs}, \t total train loss: {mean_loss}")
            if test_loader:
                score = test_model(net, test_loader, device)
                if score > best_score:
                    best_score = score
                    if save_ckpts:
                        torch.save(net.state_dict(), p_join(ckpt_save_folder, f"model_{eph}_best.ckpt"))
                print(f"Epoch: {eph}/{epochs}, \t total score test: {score}, [best score: {best_score}]")
            print()