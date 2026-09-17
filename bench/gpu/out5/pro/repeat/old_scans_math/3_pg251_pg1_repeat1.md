Since $\psi_1(x) and \psi_2(x)$ are uniformly continuous, as $\delta \rightarrow 0$ the functions $\bar{\psi}_1(x) and \bar{\psi}_2(x)$ tend uniformly to $\psi_1(x) and \psi_2(x)$ respectively, and so

$$\lim_{\delta \rightarrow 0} \int_{\bar{\psi}_1(x)}^{\bar{\psi}_2(x)} f(x, y) dy = \int_{\psi_1(x)}^{\psi_2(x)} f(x, y) dy$$

uniformly in $x$ . It follows that

$$\lim_{\delta \rightarrow 0} \int_{x_0'}^{x_1'} dx \int_{\bar{\psi}_1(x)}^{\bar{\psi}_2(x)} f(x, y) dx = \int_{x_0}^{x_1} dx \int_{\psi_1(x)}^{\psi_2(x)} f(x, y) dx.$$

On the other hand, as $\delta \rightarrow 0$ the region $\bar{R}$ tends to $R$ . Hence

$$\lim_{\delta \rightarrow 0} \iint_R f(x, y) dS = \iint_R f(x, y) dS$$

Combining the three equations, we have

$$\iint_R f(x, y) dS = \int_{x_0}^{x_1} dx \int_{\psi_1(x)}^{\psi_2(x)} f(x, y) dy.$$

The other statement can be established in a similar way.

A similar argument is available if we abandon the hypothesis

Fig 6—Non-convex regions of integration

of convexity and consider regions of the form indicated in fig. 6. We assume merely that the boundary curve of the region is intersected by every parallel to the $x$ -axis and by every parallel to the $y$ -axis in a bounded number of points or intervals. By $\int f(x, y) dy$ we then mean the sum of the integrals of the function $f(x, y)$ for a fixed $x$ , taken over all the intervals which the line $x = \text{const.}$ has in common with the closed region. For non-