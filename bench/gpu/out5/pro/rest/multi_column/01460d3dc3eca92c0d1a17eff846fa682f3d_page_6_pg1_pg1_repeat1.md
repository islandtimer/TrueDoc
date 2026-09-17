Fig. 5. The network nodes are partitioned into cluster c₁ , c₂ and c₃ . (a) The nodes \{v₂, v₃, v₄, v₅\} are the border nodes of cluster c₁ after Step II of Section III-B3b. (b) Node v₁ replaces v₂ and v₃ as the border node.

Algorithm 2: Reduce Redundant Border Nodes

1 for Each cluster cᵢ do 2 Set cluster weight as 1/(|bᵢ ∪ βᵢ|) . 3 Calculate MVC on cluster-level topology. 4 if Border node in non-VC cluster then 5 Change to the cluster-ID of neighbor VC cluster. 6 Calculate MVC on bᵢᵐ ∪ δᵢᵐ as λᵢ . 7 Select Min\{|bᵢᵐ|, |λᵢ|\} as the border nodes of cᵢᵐ .

c₂ are \{v₃, v₅, v₈, v₉\} , and the cluster border nodes between c₁ and c₃ are \{v₂, v₃, v₄, v₆, v₇\} . Secondly, the intersection area between c₁² and c₁³ becomes cluster c₁ with border nodes \{v₂, v₃, v₄, v₅\} . Although we select the minimum number of border nodes for c₁² and c₁³ , v₁ can replace v₂ and v₃ as the border node of c₁ as shown in Fig. 5(b) to further decrease the total number of border nodes. We formalize the approach to reduce redundant border nodes as follows. The main operation flow is shown in Alg. 2.

(i) We reset the cluster-ID of all the border nodes selected in Section III-B3b to a minimum number of clusters. We convert it to the Minimum Vertex Cover (MVC) problem [12] as follows. In the first place, we abstract the clusters into a cluster-level topology as shown in Fig. 6, where each cluster-level node represents a cluster. If there exists edges between two clusters as in Fig. 6.(a), we connect the two cluster-level nodes. Next, we set the weight of each node in the cluster-level topology. The border nodes in cluster cᵢ are bᵢ after Alg. 1, and we call all the other border nodes that have edge connections with cluster cᵢ as βᵢ . The nodes set bᵢ ∪ βᵢ represents the maximum set of border nodes in cᵢ if re-categorizing the cluster-ID of βᵢ . To concentrate more border nodes in fewer clusters using MVC, we set weight value to each cluster. If the number of all the possible border nodes |bᵢ ∪ βᵢ| is high, we set a low weight value to the cluster cᵢ . In the implementation, we set the weight of cluster cᵢ to 1/(|bᵢ ∪ βᵢ|) . After that, we run the MVC algorithm on the cluster-level topology. If a border node belongs to a non-VC cluster, it changes its cluster-ID to the neighbor VC cluster. To differentiate with the notations before this step, cᵢ changes to cᵢᵐ after re-categorizing the border nodes, and bᵢ changes to bᵢᵐ .

(ii) Name δᵢᵐ as the subset of cᵢᵐ - bᵢᵐ , in which each node

Fig. 6. (a) The network nodes are partitioned into clusters with different colors. (b) The clusters are abstracted into a cluster-level topology. The nodes in solid blue are vertex cover clusters.

has at least a neighbor in bᵢᵐ . To simplify the analysis, we suppose there are not sink nodes at bᵢᵐ or δᵢᵐ . The nodes in bᵢᵐ and δᵢᵐ are not in cluster-contained-subnets. Name Φᵢ = bᵢᵐ ∪ δᵢᵐ . Fig. 5(a) illustrates the example Φ₁ of c₁ . Then we calculate MVC on Φᵢ as λᵢ . We use λᵢ as alternative border nodes to bᵢᵐ . Because each edge in Φᵢ has at least one endpoint in the MVC nodes λᵢ , so monitoring λᵢ can capture all the flows passing over Φᵢ . The number of λᵢ is not necessarily smaller than bᵢᵐ . Therefore, we select Min\{|bᵢᵐ|, |λᵢ|\} as the new border nodes of cᵢᵐ . If λᵢ are selected as the border nodes of cluster cᵢᵐ , the non-VC nodes in bᵢᵐ do not need to monitor the flow, and their cluster-ID are set to the neighbor cluster.

C. Protocol for Cluster based SD-WSN

CluFlow makes the SDN controller estimate flow among clusters by monitoring the flow at border nodes. The SDN controller controls traffic flow by injecting cluster-level routing rules to the border nodes. The management procedure of the SDN controller and nodes in WSN is shown in Alg. 3.

There are at least two benefits of utilizing SDN control in cluster-level routing. Firstly, compared with SDN management for every node in WSN, CluFlow trades granularity of SDN control for less communication load. Only cluster border nodes communicate with the SDN controller. The number of nodes that communicate with the SDN controller decreases. Secondly, cluster-level routing and local routing are decoupled. The nodes inside the clusters use only distributed local routing and do not need to request flow table entries from the SDN controller. The communication delay caused by requesting flow table entries therefore decreases.

IV. EXPERIMENTAL SETUP AND RESULTS

In this section, we test and evaluate CluFlow in simulation and a real deployed WSN.

A. Benchmark Approaches

To evaluate the performance of CluFlow, three benchmark approaches are implemented to calculate the communication flow among clusters.