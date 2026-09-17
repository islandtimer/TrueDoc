each circle $K_m$ is contained in the interior of $R_\nu$ , provided $\nu$ is sufficiently large, on the other hand, every $R_\nu$ is bounded and is therefore contained in a circle $K_M$ of sufficiently large radius $M$ . Since the integrand $e^{-x^2-v^2}$ is positive everywhere, it follows that

$$\iint_{K_m} e^{-x^2-v^2} dx dy \leq \iint_{R_\nu} e^{-x^2-v^2} dx dy \leq \iint_{K_M} e^{-x^2-v^2} dx dy.$$

As $m and M$ increase, the integrals over $K_m and K_M$ have the same limit $\pi$ , so that the integral over $R_\nu$ must have the same limit, this proves that the integral must converge to the limit $\pi$ .

We obtain a particularly interesting result if for the regions $R_\nu$ we choose the squares $|x| \leq \nu, |y| \leq \nu$ . The integral $\iint_{R_\nu} e^{-x^2-v^2} dx dy$ can then be reduced to two simple integrations (of section 2, p 228):

$$\iint_{R_\nu} e^{-x^2-v^2} dx dy = \int_{-\nu}^{\nu} e^{-x^2} dx \int_{-\nu}^{\nu} e^{-y^2} dy = \left( \int_{-\nu}^{\nu} e^{-x^2} dx \right)^2 = \left( 2 \int_0^{\nu} e^{-x^2} dx \right)^2.$$

If we now let $\nu$ tend to $\infty$ , we must again obtain the same limit $\pi$ . Hence

$$\left( 2 \int_0^{\infty} e^{-x^2} dx \right)^2 = \pi$$

or

$$\int_0^{\infty} e^{-x^2} dx = \frac{1}{2} \sqrt{\pi},$$

in agreement with Vol I, p 498

5. Summary and Extensions

It is useful to consider the concepts of this section again from a single unifying point of view. Our extension of the concept of integral to cases in which the definitions in section 2 (p 224) are not immediately applicable consists in regarding the value of the integral as the limiting value of a sequence of integrals over regions $R_\nu$ , which approximate to the original region of integration $R$ as $\nu$ increases. For this purpose we regard the region $R$ as open instead of closed, we assign all the points of discontinuity of the function $f$ to the boundary and consider the boundary as not belonging to $R$ . We then say that the region is approximated to by a sequence of regions $R_1, R_2, \dots, R_n, \dots$ if all the closed regions $R_n$ lie in $R$ and every arbitrarily chosen closed sub-region in the interior of $R$ is also a sub-region of the region $R_n$ , provided only that $n$ is sufficiently large. If in particular the sub-regions $R_n$ are so chosen that each one contains the