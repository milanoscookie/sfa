# -*- coding: utf-8 -*-
"""
@author: dwlee
"""

import numpy as np
import pandas as pd
import sfa.base


def create_algorithm(abbr):
    return SignalPropagation(abbr)
# end of def
    

class SignalPropagation(sfa.base.Algorithm):
    def __init__(self, abbr):
        super().__init__(abbr)        
        self._name = "Signal propagation algorithm"
    
    def initialize(self):
        A = self._data.A        
        name_to_idx = self._data.name_to_idx 
        df_ba = self._data.df_ba # Basal activity
        
        self._x0 = np.zeros(A.shape[0])
        self._ind_ba = []
        self._val_ba = []
        for i, row in enumerate(df_ba.iterrows()):
            row = row[1]
            list_ind = [] # Indices
            list_val = [] # Values
            for target in df_ba.columns[ row.nonzero() ]:
                list_ind.append( name_to_idx[target] )
                list_val.append( row[target] )
            # end of for
            self._ind_ba.append( list_ind )
            self._val_ba.append( list_val )
        # end of for      
    
        # Mapping from the indices of adjacency to those of DataFrame
        self._iadj_to_idf = list(map(lambda x: name_to_idx[x],
                                     self._data.df_exp.columns))
    
        # Transition matrix
        self._P = self.normalize(A)
        
    # end of def
        
    def compute(self):
        print("Computing signal propagation ...")        
        alpha = self._params.alpha

        P = self._P
        df_exp = self._data.df_exp # Result of experiment

        # Simulation result
        sim_result = np.zeros(df_exp.shape, dtype=np.float)    
        
        x0 = self._x0
        # Main loop of the simulation
        for i, ind_ba in enumerate(self._ind_ba):
            x_cnt, trjx_cnt = self.propagate(P, x0, x0, a=alpha, notrj=False)
            ind_ba = self._ind_ba[i]
            x0_ba_store = x0[ ind_ba ][:]            

            x0[ ind_ba ] = self._val_ba[i] # Basal activity
            
            x_exp, trjx_exp = self.propagate(P, x0, x0, a=alpha, notrj=False)
            rel_change = ((x_exp-x_cnt)/np.abs(x_cnt))[ self._iadj_to_idf ]            
            sim_result[i, :] = rel_change                        
            x0[ ind_ba ] = x0_ba_store
        # end of for
       
        df_sim = pd.DataFrame(self._sim_result,
                              index=df_exp.index,
                              columns=df_exp.columns)
    
        # Abandon the proteins which are not included in the exp. results.
        self._result = df_sim[ df_exp.columns ]
    # end of def compute
        
    def normalize(self,
                   A,
                   norm_in=True,
                   norm_out=True):
                
        # Check whether A is a square matrix
        if A.shape[0] != A.shape[1]:
            raise ValueError("The A (adjacency matrix) should be square matrix.")
    
        # Build propagation matrix P from A
        P = A.copy()
    
        # Norm. in-degree
        if norm_in == True:
            sum_col_A = np.abs(A).sum(axis=0)
            sum_col_A[sum_col_A==0] = 1
            if norm_out == False:
                Dc = 1/sum_col_A
            else:
                Dc = 1/np.sqrt(sum_col_A)
            # end of else
            P = Dc*P # This is not matrix multiplication
    
        # Norm. out-degree
        if norm_out == True:
            sum_row_A = np.abs(A).sum(axis=1)
            sum_row_A[sum_row_A==0] = 1
            if norm_in == False:
                Dr = 1/sum_row_A
            else:
                Dr = 1/np.sqrt(sum_row_A)
            # end of row
            P = np.multiply(P, np.mat(Dr).T)
            # Converting np.mat to ndarray
            # does not cost a lot.
            P = P.A
        # end of if
        """
        The normalization above is the same as the follows:
        >>> np.diag(Dr).dot(A.dot(np.diag(Dc)))
        """
        return P
    # end of def normalize
    
    def propagate(P,
                  xi,
                  b,
                  a=0.5,
                  lim_iter=1000,
                  tol=1e-5,
                  notrj=True):
        """
        Nework propagation based on the valve concept.
    
        Parameters
        ------------------
        P: numpy.ndarray
            adjacency matrix (stochastic matrix)
        xi: numpy.ndarray
            Initial state
        b: numpy.ndarray
            Basal activity
        a: real number (optional)
            Propagation rate.
        lim_iter: integer (optioanl)
            Limitation of iterations for propagation.
            Propagation terminates, when the iteration is reached.
        tol: real number (optional)
            Tolerance for terminating iteration
            Iteration continues, if Frobenius norm of (x(t+1)-x(t)) is
            greater than tol.
        notrj: bool (optional)
            Determine whether trajectory of the state and propagation matrix
            is returned. If notrj is true, the trajectories are not returned.
    
        Returns
        -------
        xp: numpy.ndarray
            State after propagation
        trj_x: numpy.ndarray
            Trajectory of the state transition
    
        See also
        --------
        """
    
        # Check whether A is a square matrix
        if P.shape[0] != P.shape[1]:
            raise ValueError("The P (stochastic matrix) should be square matrix.")
    
        n = P.shape[0] # Size of adjacency matrix
    
        # Check the size of xi
        if len(xi) != n:
            raise ValueError("The dimension of the initial state " \
                             "is not consistent with A (adjacency matrix).")
    
    
        # Initial values
        x0 = np.zeros((n,), dtype=np.float)
        x0[:] = xi
    
        x_t1 = x0.copy()
        trj_x = []
    
        # Record the initial states
        trj_x.append( x_t1.copy() )
    
        # Main loop
        num_iter = 0
        for i in range(lim_iter):
            # Main formula
            x_t2 = a*P.dot(x_t1) + (1-a)*b
            num_iter += 1
            # Check termination condition
            if np.linalg.norm(x_t2 - x_t1)<=tol:
                break
    
            # Add the current state to the trajectory
            if not notrj:
                trj_x.append( x_t2 )
    
            # Update the state
            x_t1 = x_t2.copy()
        # end of for
    
        if notrj is True:
            return x_t2, num_iter
        else:
            return x_t2, np.array(trj_x)
    # end of def
            
# end of class