The rational function ψₛ+₂(-hA) is uniformly bounded and satisfies ψₛ+₂(0) = 0 due to (15a). The second and third term of (16) are thus bounded as in the previous theorem. For the term with ψₛ+₁ , we use the fact that due to (12) and (15b)

$$ψₛ+₁(-hA) = ψₛ+₁(-hA) - ψₛ+₁(0) = hA . ψₛ+₁⁽¹⁾(-hA)$$

with ψₛ+₁⁽¹⁾(0) = 0 . Thus, we have

$$hˢ⁺¹ ψₛ+₁(-hA) f⁽ˢ⁾(tₙ) = hˢ⁺¹⁺β ψₛ+₁⁽¹⁾(-hA) (h\tilde{A})¹⁻β . A\tilde{A}⁻¹ . \tilde{A}β f⁽ˢ⁾(tₙ).$$

With the help of Lemma 2, this term can be bounded in the desired way, which concludes the proof. □

Remark The restriction to β ≤ 1 in Theorem 3 was made just for simplicity. If the source term has higher spatial regularity, and if further conditions of the type (15) are fulfilled, then we can also show higher temporal order of convergence. The additional conditions can be derived by expanding the defect in (16) even further, and it can be shown as in Lemma 3 that they are implied by the underlying quadrature rule being of higher order. In particular, full (classical) order is achieved for sufficiently smooth source term with periodic boundary conditions.

Example To illustrate the sharpness of the bounds in Theorem 3, we consider the linear parabolic problem

$$∂ U/∂ t(x, t) - ∂² U/∂ x²(x, t) = (2 + x(1 - x))eᵗ \quad (17)$$

for x ∈ [0, 1] and t ∈ [0, 1] , subject to homogeneous Dirichlet boundary conditions. For the initial value $x(1 - x)$ , the exact solution is U(x, t) = x(1 - x)eᵗ .

We discretize this problem in space by standard finite differences, and in time by the exponential 2-stage Gauss method, respectively. The numerically observed temporal orders of convergence in different norms are displayed in Table 1.

<table> <thead> <tr> <th>N</th> <th>H¹</th> <th>L¹</th> <th>L²</th> <th>L∞</th> </tr> </thead> <tbody> <tr> <td>50</td> <td>2.80</td> <td>3.53</td> <td>3.27</td> <td>3.00</td> </tr> <tr> <td>100</td> <td>2.76</td> <td>3.50</td> <td>3.26</td> <td>3.01</td> </tr> <tr> <td>200</td> <td>2.75</td> <td>3.50</td> <td>3.25</td> <td>3.00</td> </tr> </tbody> </table>

Table 1

Numerically observed temporal orders of convergence in different norms for discretizations with N spatial degrees of freedom and h = 1/128 .

The attainable value of β in Theorem 3 relies on the characterization of the domains of fractional powers of elliptic operators. The source function in (17)