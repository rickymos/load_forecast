import pandas as pd
import tensorflow as tf
import numpy as np
import time
import matplotlib.pyplot as plt
import getWeekday
import predict_util
from os import listdir


#### get a list of buildings #### 
def getBldMap():
    bld_names = []
    
    #for file in listdir('F:/OneDrive/Load Forecast/tf_nn/data'):
    for file in listdir('F:/SkyDrive/Load Forecast/tf_nn/data'):
        bld_name = str(file[:-4])
        bld_names.append(bld_name)

    return bld_names


#### add one neural network layer ####
def add_layer(inputs, in_size, out_size, activation_function=None):
    Weights = tf.Variable(tf.random_normal([in_size, out_size]))
    biases = tf.Variable(tf.zeros([1, out_size]) + 0.1)
    Wx_plus_b = tf.matmul(inputs, Weights) + biases
    if activation_function is None:
        outputs = Wx_plus_b
    else:
        outputs = activation_function(Wx_plus_b)
    return (outputs, Weights, biases)


### add RBF layer ####
def RBF_layer(inputs, in_size, out_size):
    centroids = tf.Variable(tf.random_uniform([out_size, in_size]) )
    var = tf.Variable(tf.truncated_normal([out_size],mean=50,stddev=10))
    #For now, we collect the distanc
    exp_list = []
    for i in range(out_size):
        exp_list.append(tf.exp((-1*tf.reduce_sum(tf.square(tf.subtract(inputs,centroids[i,:])),1))/(2*var[i])))
        outputs = tf.transpose(tf.stack(exp_list))
    return(outputs, centroids, var)

    
#### neural network forecast
def NN_forecast(bld_name, n_train, n_lag, T):
    ############################ Iteration Parameter ##########################
    # maximum iteration
    Max_iter = 20000
    # stopping criteria
    epsilon = 1e-3
    last_l = 10000
        
    ############################ TensorFlow ###################################    
    # place holders
    xs = tf.placeholder(tf.float32, [None, T * n_lag])
    ys = tf.placeholder(tf.float32, [None, T])
    
    N_neuron = 50
    # hidden layers
    (l1, w1, b1) = RBF_layer(xs, T * n_lag, N_neuron)
    #(l2, w2, b2) = add_layer(l1, N_neuron, N_neuron, activation_function=tf.nn.tanh)
    
    # output layer
    (prediction, wo, bo) = add_layer(l1, N_neuron, T, None)
    
    # loss function, RMSPE
    #loss = tf.reduce_mean(tf.reduce_sum(tf.square(ys - prediction), 1))  
    loss = T * tf.reduce_mean(tf.square(ys - prediction) )  
    
    loss += 1e-2 * ( tf.nn.l2_loss(wo) + tf.nn.l2_loss(bo) )
    #loss += 1e-2 * ( tf.nn.l2_loss(w2) + tf.nn.l2_loss(b2) )
    
    # training step
    train_step = tf.train.AdamOptimizer().minimize(loss)
    
    # init.
    init = tf.global_variables_initializer()
    # run
    sess = tf.Session()
    sess.run(init)    
    
    
    ###########################################################################
    
    load_weekday = getWeekday.getWeekdayload(bld_name)
    max_load = np.max(load_weekday)
    #max_load = 1
    n_days = int(load_weekday.size / T)
    ################## generate data ##########################################
    MAPE_sum = 0.0
    RMSPR_sum = 0.0
    
    for curr_day in range(n_train + n_lag, n_days-1):
        y_train = np.zeros((n_train, T))
        X_train = np.zeros((n_train, T * n_lag))

        
        row = 0
        for train_day in range(curr_day - n_train, curr_day):
            y_train[row,:] = load_weekday[train_day * T : train_day * T + T]
            X_train[row,0*T*n_lag:1*T*n_lag] = load_weekday[train_day * T - n_lag * T: train_day * T]
            row += 1
            
        max_load = np.max(X_train)
        min_load = np.min(X_train)    
        # building test data
        X_test = np.zeros((1, T * n_lag))
        X_test[0, 0*T*n_lag:1*T*n_lag] = load_weekday[curr_day*T - n_lag*T: curr_day*T]
        y_test = load_weekday[curr_day*T: curr_day *T + T]
        
        X_train = (X_train-min_load) / (max_load - min_load)
        y_train = (y_train-min_load) / (max_load - min_load)
        X_test = (X_test-min_load) / (max_load - min_load)
        #y_test = (y_test-min_load) / (max_load - min_load)
                

        # training 
        
        i = 0
        while (i < Max_iter):
            # training
            (t_step, l) = sess.run([train_step, loss], feed_dict={xs: X_train, ys: y_train})
            if(abs(last_l - l) < epsilon):
                break
            else:
                last_l = l
                i = i+1
        '''
        i = 0
        while (i < Max_iter):
            # training
            (t_step, l) = sess.run([train_step, loss], feed_dict={xs: X_train, ys: y_train})
            if(i % 100 == 0):
                print(l)
                y_pred = prediction.eval(session = sess, feed_dict={xs: X_test})
                
                mape = predict_util.calMAPE(y_test, y_pred)
                rmspe = predict_util.calRMSPE(y_test, y_pred)
                print('MAPE: %.2f, RMSPE: %.2f' % (mape, rmspe))
            i = i+1
        '''
            
        
        #y_ = prediction.eval(session = sess, feed_dict={xs: X_train})
        y_pred = prediction.eval(session = sess, feed_dict={xs: X_test})
        y_pred = y_pred * (max_load - min_load) + min_load
        # plot daily forecast
        '''
        xaxis = range(T)
        plt.plot(xaxis, y_pred.flatten(), 'r')
        plt.plot(xaxis, y_test.flatten(), 'g')
        plt.show()
        '''

        mape = predict_util.calMAPE(y_test, y_pred)
        rmspe = predict_util.calRMSPE(y_test, y_pred)

        # update error metric results
        #print('MAPE: %.2f, RMSPE: %.2f' % (mape, rmspe))
        MAPE_sum += mape
        RMSPR_sum += rmspe
        

    # close session
    tf.reset_default_graph() # reset the graph 
    sess.close() 
    

    
    days_sample = n_days - 1 - n_train - n_lag

    return (MAPE_sum / days_sample, RMSPR_sum / days_sample)

    
if __name__ == "__main__":
    # number of days in training set    
    n_train = 50
    # number of lags
    n_lag = 5
    # time intervals per day
    T= 96
   

    ############################ building data  ############################
    bld_names = getBldMap()

    
    nn_MAPE = []
    nn_RMSPE = []
    for bld_name in bld_names:
        t = time.time()
        print("forecasting building： " + bld_name + "...")
        load_weekday = getWeekday.getWeekdayload(bld_name)
        (MAPE_avg_nn, RMSPE_avg_nn) = NN_forecast(bld_name, n_train, n_lag, T)
        nn_MAPE.append(MAPE_avg_nn)
        nn_RMSPE.append(RMSPE_avg_nn)
        print('forecast result MAPE: %.2f, RMSPE: %.2f' % (MAPE_avg_nn, RMSPE_avg_nn))
        elapsed = time.time() - t
        print('elapsed time is : %.2f' % elapsed)
        
    d = dict({'bld_name' : bld_names, 'nn_MAPE' : nn_MAPE, 'nn_RMSPE' : nn_RMSPE})
    df = pd.DataFrame(d)    
    df.to_csv('benchmark_forecast_results.csv', sep=',', index = False)
    
    
    '''
    bld_name = '1008_EE_CSE_WA3_accum'
    print("forecasting building： " + bld_name + "...")
    load_weekday = getWeekday.getWeekdayload(bld_name)
    (MAPE_avg_nn, RMSPE_avg_nn) = NN_forecast(bld_name, n_train, n_lag, T)
    print('forecast result MAPE: %.2f, RMSPE: %.2f' % (MAPE_avg_nn, RMSPE_avg_nn))
    '''