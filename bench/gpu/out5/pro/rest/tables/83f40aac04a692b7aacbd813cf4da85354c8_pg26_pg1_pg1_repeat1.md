<table> <thead> <tr> <th>Data set</th> <th>n</th> <th>m</th> <th>Ratio</th> </tr> </thead> <tbody> <tr> <td>Cancer</td> <td>3.9k</td> <td>217</td> <td>1.14</td> </tr> <tr> <td>Amazon</td> <td>500k</td> <td>10k</td> <td>1.76</td> </tr> <tr> <td>Muscle</td> <td>220k</td> <td>22k</td> <td>2.47</td> </tr> </tbody> </table>

Table 2: Timing the Hessian bound optimization scheme.

5. Software

We provide two software solutions in relation to the current paper. An R package, msg1 , with a relatively simple interface to our multinomial and logistic sparse group lasso regression routines. In addition, a C++ template library, sgl , is provided. The sgl template library gives access to the generic sparse group lasso routines. The R package relies on this library. The sgl template library relies on several external libraries. We use the Armadillo C++ library [14] as our primary linear algebra engine. Armadillo is a C++ template library using expression template techniques to optimize the performance of matrix expressions. Furthermore we utilize several Boost libraries [15]. Boost is a collection of free peer-reviewed C++ libraries, many of which are template libraries. For an introduction to these libraries see for example [16]. Use of multiple processors for cross validation and subsampling is supported through OpenMP [17].

The msg1 R package is available from CRAN. The sgl library is available upon request.

5.1. Run-time performance

Table 3 lists run-times of the current multinomial sparse group lasso implementation for three real data examples. For comparison, the glmnet uses 5.2s, 8.3s and 137.0s, respectively, to fit the lasso path for the three data sets in Table 3. The glmnet is a fast implementation of the coordinate descent algorithm for fitting generalized linear models with the lasso penalty or the elastic net penalty [10]. The glmnet cannot be used to fit models with group lasso or sparse group lasso penalty.

6. Conclusion

We developed an algorithm for solving the sparse group lasso optimization problem with a general convex loss function. Furthermore, convergence