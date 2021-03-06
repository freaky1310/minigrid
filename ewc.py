import torch
from torch import nn
from torch.nn import functional as F
from torch.autograd import Variable as V
import torch.utils.data

# Generate a register buffer for the mean and for the fisher diagonal matrix. It must be
# used after a FIM has been calculated but before the ewc_loss().
def consolidate(model, fisher):
    print("Consolidating named_parameters.")
    for n, p in model.named_parameters():
        n = n.replace('.', '__')
        model.register_buffer('{}_estimated_mean'.format(n), p.data.clone())
        model.register_buffer('{}_estimated_fisher'.format(n), fisher[n].data)
    print("Parameters consolidated.")

# Calculate the ewc loss, which has to be added to the current task loss. If one or more
# attribute hasn't been consolidated, return 0 instead.
def ewc_loss(model, importance):
    try:
        losses = []
        for n, p in model.named_parameters():
            # retrieve the consolidated mean and fisher information.
            n = n.replace('.', '__')
            mean = getattr(model, '{}_estimated_mean'.format(n))
            fisher = getattr(model, '{}_estimated_fisher'.format(n))
            # wrap mean and fisher in Vs.
            mean = V(mean)
            fisher = V(fisher.data)
            # calculate a ewc loss. (assumes the parameter's prior as
            # gaussian distribution with the estimated mean and the
            # estimated cramer-rao lower bound variance, which is
            # equivalent to the inverse of fisher information)
            losses.append((fisher * (p-mean)**2).sum())
        return (importance/2)*sum(losses)
    except AttributeError:
        # ewc loss is 0 if there's no consolidated parameters.
        return V(torch.zeros(1))