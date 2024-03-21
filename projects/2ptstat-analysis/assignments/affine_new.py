import tensorflow as tf
import numpy as np
from tqdm import trange


def affine_sample(log_prob, n_steps, current_state, args=[], progressbar=True):
    
    # split the current state
    current_state1, current_state2 = current_state
    
    # pull out the number of parameters and walkers
    n_walkers, n_params = current_state1.shape

    # initial target log prob for the walkers (and set any nans to -inf)...
    logp_current1= log_prob(current_state1, *args)
    logp_current2 = log_prob(current_state2, *args)
    logp_current1 = tf.where(tf.math.is_nan(logp_current1), tf.ones_like(logp_current1)*tf.math.log(0.), logp_current1)
    logp_current2 = tf.where(tf.math.is_nan(logp_current2), tf.ones_like(logp_current2)*tf.math.log(0.), logp_current2)

    logp_current1 = tf.where(tf.math.greater(logp_current1, 0), tf.ones_like(logp_current1)*tf.math.log(0.), logp_current1)
    logp_current2 = tf.where(tf.math.greater(logp_current2, 0), tf.ones_like(logp_current2)*tf.math.log(0.), logp_current2)

    # holder for the whole chain
    chain = [tf.expand_dims(tf.concat([current_state1, current_state2], axis=0), axis=0)]

    logp_chain = [tf.expand_dims(tf.concat([logp_current1, logp_current2], axis=0), axis=0)]
    
    # progress bar?
    loop = trange if progressbar else range

    # MCMC loop
    for epoch in loop(1, n_steps):

        # first set of walkers:

        # proposals
        partners1 = tf.gather(current_state2, np.random.randint(0, n_walkers, n_walkers))
        z1 = 0.5*(tf.random.uniform([n_walkers], minval=0, maxval=1)+1)**2
        proposed_state1 = partners1 + tf.transpose(z1*tf.transpose(current_state1 - partners1))

        # target log prob at proposed points
        logp_proposed1 = log_prob(proposed_state1, *args)
        logp_proposed1 = tf.where(tf.math.is_nan(logp_proposed1), tf.ones_like(logp_proposed1)*tf.math.log(0.), logp_proposed1)
        logp_proposed1 = tf.where(tf.math.greater(logp_proposed1, 0), tf.ones_like(logp_proposed1)*tf.math.log(0.), logp_proposed1)

        # acceptance probability
        p_accept1 = tf.math.minimum(tf.ones(n_walkers), z1**(n_params-1)*tf.exp(logp_proposed1 - logp_current1) )

        # accept or not
        accept1_ = (tf.random.uniform([n_walkers], minval=0, maxval=1) <= p_accept1)
        accept1 = tf.cast(accept1_, tf.float32)

        # update the state
        current_state1 = tf.transpose( tf.transpose(current_state1)*(1-accept1) + tf.transpose(proposed_state1)*accept1)
        logp_current1 = tf.where(accept1_, logp_proposed1, logp_current1)

        # second set of walkers:

        # proposals
        partners2 = tf.gather(current_state1, np.random.randint(0, n_walkers, n_walkers))
        z2 = 0.5*(tf.random.uniform([n_walkers], minval=0, maxval=1)+1)**2
        proposed_state2 = partners2 + tf.transpose(z2*tf.transpose(current_state2 - partners2))

        # target log prob at proposed points
        logp_proposed2= log_prob(proposed_state2, *args)
        logp_proposed2 = tf.where(tf.math.is_nan(logp_proposed2), tf.ones_like(logp_proposed2)*tf.math.log(0.), logp_proposed2)
        logp_proposed2 = tf.where(tf.math.greater(logp_proposed2, 0), tf.ones_like(logp_proposed2)*tf.math.log(0.), logp_proposed2)

        # acceptance probability
        p_accept2 = tf.math.minimum(tf.ones(n_walkers), z2**(n_params-1)*tf.exp(logp_proposed2 - logp_current2) )

        # accept or not
        accept2_ = (tf.random.uniform([n_walkers], minval=0, maxval=1) <= p_accept2)
        accept2 = tf.cast(accept2_, tf.float32)

        # update the state
        current_state2 = tf.transpose( tf.transpose(current_state2)*(1-accept2) + tf.transpose(proposed_state2)*accept2)
        logp_current2 = tf.where(accept2_, logp_proposed2, logp_current2)

        # append to chain
        chain.append(tf.expand_dims(tf.concat([current_state1, current_state2], axis=0), axis=0))

        logp_chain.append(tf.expand_dims(tf.concat([logp_current1, logp_current2], axis=0), axis=0))
        

    
    # stack up the chain and return    
    return tf.concat(chain, axis=0),tf.concat(logp_chain, axis=0)

# state variables have shape: (n_walkers, n_batch, n_params)
def affine_sample_batch(log_prob, n_steps, current_state, args=[], progressbar=True):
    
    # split the current state
    current_state1, current_state2 = current_state
    
    # pull out the number of parameters and walkers
    n_walkers, n_batch, n_params = current_state1.shape

    # initial target log prob for the walkers (and set any nans to -inf)...
    logp_current1 = log_prob(current_state1, *args)
    logp_current2 = log_prob(current_state2, *args)
    logp_current1 = tf.where(tf.math.is_nan(logp_current1), tf.ones_like(logp_current1)*tf.math.log(0.), logp_current1)
    logp_current2 = tf.where(tf.math.is_nan(logp_current2), tf.ones_like(logp_current2)*tf.math.log(0.), logp_current2)

    # holder for the whole chain
    chain = [tf.expand_dims(tf.concat([current_state1, current_state2], axis=0), axis=0)]

    # progress bar?
    loop = trange if progressbar else range
    
    # MCMC loop
    for epoch in loop(1, n_steps):

        # first set of walkers:

        # proposals
        partners1 = tf.gather(current_state2, np.random.randint(0, n_walkers, n_walkers))
        z1 = 0.5*(tf.random.uniform([n_walkers, n_batch], minval=0, maxval=1)+1)**2
        proposed_state1 = partners1 + tf.transpose(z1*tf.transpose(current_state1 - partners1, perm=[2, 0, 1]), perm=[1, 2, 0])

        # target log prob at proposed points
        logp_proposed1 = log_prob(proposed_state1, *args)
        logp_proposed1 = tf.where(tf.math.is_nan(logp_proposed1), tf.ones_like(logp_proposed1)*tf.math.log(0.), logp_proposed1)

        # acceptance probability
        p_accept1 = tf.math.minimum(tf.ones([n_walkers, n_batch]), z1**(n_params-1)*tf.exp(logp_proposed1 - logp_current1) )

        # accept or not
        accept1_ = (tf.random.uniform([n_walkers, n_batch], minval=0, maxval=1) <= p_accept1)
        accept1 = tf.cast(accept1_, tf.float32)

        # update the state
        current_state1 = tf.transpose( tf.transpose(current_state1, perm=[2, 0, 1])*(1-accept1) + tf.transpose(proposed_state1, perm=[2, 0, 1])*accept1, perm=[1, 2, 0])
        logp_current1 = tf.where(accept1_, logp_proposed1, logp_current1)

        # second set of walkers:

        # proposals
        partners2 = tf.gather(current_state1, np.random.randint(0, n_walkers, n_walkers))
        z2 = 0.5*(tf.random.uniform([n_walkers, n_batch], minval=0, maxval=1)+1)**2
        proposed_state2 = partners2 + tf.transpose( z2*tf.transpose(current_state2 - partners2, perm=[2, 0, 1]), perm=[1, 2, 0])

        # target log prob at proposed points
        logp_proposed2 = log_prob(proposed_state2, *args)
        logp_proposed2 = tf.where(tf.math.is_nan(logp_proposed2), tf.ones_like(logp_proposed2)*tf.math.log(0.), logp_proposed2)

        # acceptance probability
        p_accept2 = tf.math.minimum(tf.ones([n_walkers, n_batch]), z2**(n_params-1)*tf.exp(logp_proposed2 - logp_current2) )

        # accept or not
        accept2_ = (tf.random.uniform([n_walkers, n_batch], minval=0, maxval=1) <= p_accept2)
        accept2 = tf.cast(accept2_, tf.float32)

        # update the state
        current_state2 = tf.transpose( tf.transpose(current_state2, perm=[2, 0, 1])*(1-accept2) + tf.transpose(proposed_state2, perm=[2, 0, 1])*accept2, perm=[1, 2, 0])
        logp_current2 = tf.where(accept2_, logp_proposed2, logp_current2)

        # append to chain
        chain.append(tf.expand_dims(tf.concat([current_state1, current_state2], axis=0), axis=0))

    # stack up the chain and return
    return tf.concat(chain, axis=0)