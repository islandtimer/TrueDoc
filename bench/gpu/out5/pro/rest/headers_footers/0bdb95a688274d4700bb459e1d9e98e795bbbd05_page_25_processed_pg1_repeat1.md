Using Google Earth KML

<Mashup> <Markers> <Marker type="General" lat="45.512362" lng="-122.687426"> <Landmark type="General" name="Simon Benson Library"> <Address>1803 SW Park Avenue, Portland, OR</Address> <Info>Visitor Center, Alumni Center</Info> <MoreInfo>www.fap.pdx.edu/.../index.html</MoreInfo> </Landmark> </Marker> <Marker lat="45.512742" lng="-122.687426"> <Landmark type="Housing" name="King Albert"> <Landmark type="Dining" name="Metro Cafe"> </Landmark> </Marker> </Markers> <Config> <Title>Portland State University Campus Map</Title> <Center lat="45.51112884101..." lng="-122.687426"/> <Zoom level="1"/> <Marker type="General" iconBase="greenIcons"> </Marker> </Config> </Mashup>

Markers

<xsl:template match="Marker" mode="icon"> <xsl:param name="landmarkType"/> <xsl:param name="position"/> <xsl:choose> <xsl:when test="string-length(@iconBase) > 0"> <xsl:choose> <xsl:when test="contains(@iconBase, 'green')"> <xsl:value-of select="@iconBase"/> </xsl:when> <xsl:otherwise> <xsl:value-of select="concat('green', @iconBase)"/> </xsl:otherwise> </xsl:choose> </xsl:when> <xsl:otherwise> <xsl:value-of select="@iconBase"/> </xsl:otherwise> </xsl:choose> </xsl:template>

Transformation