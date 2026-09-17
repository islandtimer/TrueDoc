Cont... (distribution time)

In P2P architecture:

• In P2P, when a peer receives some file data, it can use its own upload capacity to redistribute the data to other peers.

Calculating the distribution time for the P2P architecture is somewhat more complicated. A simple expression for the minimal distribution time:

• Step1: At the beginning, only the server has the file.

• To get this file into the community of peers, minimum distribution time is at least $F/u_{s}$.

• Step2: the peer with the lowest download rate cannot obtain all F bits of the file in less than $F/d_{min}$ seconds.

• Step3: the total upload capacity of the system is, $u_{total} = u_{s} + u_{1} + \ldots + u_{N}$.

– The system must deliver (upload) F bits to each of the N peers.

– This cannot be done at a rate faster than $u_{total}$.

– So, the minimum distribution time is also at least $NF/(u_{s} + u_{1} + \ldots + u_{N})$.

• Finally, the minimum distribution time for P2P

$$D _ {\mathrm {P 2 P}} \geq \max \left\{\frac {F}{u _ {s}}, \frac {F}{d _ {m i n}}, \frac {N F}{u _ {s} + \sum_ {i = 1} ^ {N} u _ {i}} \right\}$$