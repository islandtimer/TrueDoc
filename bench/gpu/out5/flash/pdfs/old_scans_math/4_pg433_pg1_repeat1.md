489. If each element of a column is multiplied by the same number, and the products be added to (or subtracted from) the corresponding elements of another column, the determinant is not altered.

According to the preceding paragraph we have

$$\begin{vmatrix} a_1 \pm mb_1 & b_1 & c_1 \\ a_2 \pm mb_2 & b_2 & c_2 \\ a_3 \pm mb_3 & b_3 & c_3 \end{vmatrix} = \begin{vmatrix} a_1 & b_1 & c_1 \\ a_2 & b_2 & c_2 \\ a_3 & b_3 & c_3 \end{vmatrix} \pm \begin{vmatrix} mb_1 & b_1 & c_1 \\ mb_2 & b_2 & c_2 \\ mb_3 & b_3 & c_3 \end{vmatrix}.$$

But the last determinant equals

$$m \begin{vmatrix} b_1 & b_1 & c_1 \\ b_2 & b_2 & c_2 \\ b_3 & b_3 & c_3 \end{vmatrix} \text{ and hence vanishes (§ 485).}$$

Ex. Evaluate $\begin{vmatrix} 4244 & 4245 \\ 4246 & 4247 \end{vmatrix}.$

The determinant $= \begin{vmatrix} 4244 & 4245 \\ 2 & 2 \end{vmatrix} = \begin{vmatrix} 4244 & 1 \\ 2 & 0 \end{vmatrix} = -2.$

490. Evaluation of determinants. By means of the preceding proposition all elements but one in a column (or row) can be made equal to zero, and hence the determinant can be reduced to one of the next lower order (§ 480). In many cases, however, the determinant, before reduction to a lower order, should be simplified as follows:

(1) Remove factors common to all elements in a row or a column.

(2) Diminish the absolute values of the elements by subtracting the corresponding elements of other columns (or rows) or multiples of these elements.