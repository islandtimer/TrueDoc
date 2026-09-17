(39.) $\int \frac{\sqrt{x} dx}{\sqrt{a^3 - x^3}}$ . Let $x^3 = z^2$

$$x = z^{\frac{2}{3}}, \quad dx = \frac{2}{3} z^{-\frac{1}{3}} dz, \quad \sqrt{x} = z^{\frac{1}{3}}, \therefore \int \frac{\sqrt{x} dx}{\sqrt{a^3 - x^3}} = \frac{2}{3} \int \frac{dz}{\sqrt{a^3 - z^2}} = \frac{2}{3} \sin^{-1} \frac{z}{a^{\frac{3}{2}}} = \frac{2}{3} \sin^{-1} \frac{x^{\frac{2}{3}}}{a^{\frac{3}{2}}} \text{Let } \theta = \sin^{-1} \frac{x^{\frac{2}{3}}}{a^{\frac{3}{2}}}, \quad \sin \theta = \frac{x^{\frac{2}{3}}}{a^{\frac{3}{2}}}, \tan \theta = \frac{\sin \theta}{\sqrt{1 - \sin^2 \theta}} = \frac{x^{\frac{2}{3}}}{\sqrt{a^3 - x^3}}, \therefore \int \frac{\sqrt{x} dx}{\sqrt{a^3 - x^3}} = \frac{2}{3} \tan^{-1} \sqrt{\frac{x^3}{a^3 - x^3}}.$$

(40.) $\int \frac{dx}{(2ax + x^2)^{\frac{3}{2}}} = \int \frac{dx}{((x+a)^2 - a^2)^{\frac{3}{2}}}$

$$\text{Let } x + a = \frac{1}{z}, \quad dx = -\frac{dz}{z^2} = - \int \frac{dz}{z^2 \left( \frac{1}{z^2} - a^2 \right)^{\frac{3}{2}}} = - \int \frac{z dz}{(1 - a^2 z^2)^{\frac{3}{2}}}.$$