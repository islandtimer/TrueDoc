Table 1. Dimensions of the CEA

<table> <thead> <tr> <th>Parameter</th> <th>Sign</th> <th>Initial amount</th> <th>Unit</th> </tr> </thead> <tbody> <tr> <td>Depth</td> <td>H</td> <td>63</td> <td>μm</td> </tr> <tr> <td>Width of expansion</td> <td>WE</td> <td>50</td> <td>μm</td> </tr> <tr> <td>Width of contraction region</td> <td>WC</td> <td>350</td> <td>μm</td> </tr> <tr> <td>Length of the contraction region</td> <td>LC</td> <td>1200</td> <td>μm</td> </tr> <tr> <td>Length of the expansion region</td> <td>LE</td> <td>700</td> <td>μm</td> </tr> <tr> <td>Number of contraction region</td> <td>NC</td> <td>6</td> <td>-</td> </tr> <tr> <td>Degree between two inlet valves</td> <td>θ</td> <td>100</td> <td>deg</td> </tr> <tr> <td>Particle-fluid flowrate</td> <td>QP</td> <td>0.3</td> <td>ml/hr</td> </tr> <tr> <td>Focusing-fluid flowrate</td> <td>QF</td> <td>6</td> <td>ml/hr</td> </tr> <tr> <td>Ratio of particle-fluid to focusing-fluid</td> <td>η=QF/QP</td> <td>20</td> <td>-</td> </tr> </tbody> </table>

Figure 1. A: The CEA and B: the smCEA drawn in COMSOL multiphysic.

same as Dean vortices are created in the entrance of contraction region, where the flow is accelerated 15, 16,22-24 . Our CTC separation device is a straight channel with contraction arrays that separates the cells based on their sizes.

Materials and Methods

COMSOL simulation

There are several empirical studies on inertial microfluidic separation devices. However, to our knowledge, no group has focused on the computational simulation of these devices. In this study, simulation was conducted based on the data from a past empirical work called the Contraction Expansion Array (CEA) as a reference (Figure 1A) to verify the simulations 16 . The CEA is a straight channel with six contraction regions, two inlets, and two outlets. The dimensions of the CEA are in table 1. The general objective in this part is to modify the configuration of the system to improve the separation efficiency. From theory, it is known that both Dean Drag force and inertial lift force are affected by the geometry of the channel. Hence, manipulating the channel geometry can affect the separation. The design of the CEA was elaborated by manipulating its geometry with a software. The software COMSOL Multiphysics 5.2® was used to simulate the 3D module of the particles flowing in the CEA. Primary assumptions were about rigid spherical particles diffused in a laminar flow of a liquid with the characteristics of water. Laminar flow and particle tracing physics are the physics used in COMSOL

Figure 2. Fabricated device prepared with soft lithography.

environment. Dean drag force equation is assumed to follow stokes drag equation all over the device and the inertial lift force term was inserted manually, different for contractions and expansions regions. Then, the effect of the angle between two inlets, the depth of the channel, the shape of expansion arrays and the ratio between the two inlet flow rates with simulation were evaluated. Figure 1B shows the properties of the optimized CEA according to simulation results. The optimized device is called the simulation-modified CEA (smCEA).

Fabrication of the design

The smCEA was fabricated according to the simulation outcome. The smCEA, similar to the CEA, has two inlets for a flow containing cells (particle fluid) and a particle-less fluid with the same physical characteristics (focusing fluid) to focus on the particles, and two outlets. The devices were prepared by soft lithography protocol 25 . In this method, molds of the smCEA were prepared with SU-8 photoresist on a glass substrate following the conventional photolithography process. Then, Poly Di-methyl Siloxane (PDMS) and its curing agent (Sylgard 184; Dow Corning, MI) in a ratio of 10:1 were poured on stamps and cured in a 65°oven overnight. The PDMS layer was detached from the stamp and bonded to a glass slide by treating both surfaces with an air-plasma treatment process in low pressure (500 mTorr) chamber (Figure 2). The plasma treatment process made PDMS hydrophilic.

Sample preparation

Two approaches in the preparation of the particle fluid were used while the focusing fluid was the same during the experiments. PBS was used as the focusing fluid. For the first set of experiment, a combination of fixed mouse fibroblast cell line (L929) (10-15 μm in diameter) and breast cancer cell line (MCF7) (18-25 μm in diameter) with a predefined density was suspended in PBS to form the particle fluid. For the second set of experiment, first, the whole blood was diluted 100 times with PBS, and then a suspension of MCF7 fixed cells was spiked into the blood. Whole blood was obtained from Iranian Blood Transfusion Organization (IBTO).