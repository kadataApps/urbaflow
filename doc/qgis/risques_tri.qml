<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.40.0" styleCategories="All" hasScaleBasedVisibilityFlag="0" simplifyAlgorithm="0" simplifyDrawingTol="1" simplifyLocal="1" simplifyDrawingHints="1" maxScale="0" minScale="100000000">
  <renderer-v2 type="categorizedSymbol" enableorderby="0" attr="concat(&quot;typ_inond&quot;, '_', &quot;scenario&quot;)" symbollevels="0" forceraster="0">
    <categories>
      <category value="03_01For" symbol="0" label="Submersion marine - aléa de forte probabilité" render="true"/>
      <category value="03_02Moy" symbol="1" label="Submersion marine - aléa de moyenne probabilité" render="true"/>
      <category value="03_03Mcc" symbol="2" label="Submersion marine - aléa moyen avec changement climatique à 100 ans" render="true"/>
      <category value="03_04Fai" symbol="3" label="Submersion marine - aléa de faible probabilité" render="true"/>
    </categories>
    <symbols>
      <symbol name="0" type="fill" clip_to_extent="1" alpha="0.7" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <Option type="Map"><Option name="color" type="QString" value="35,95,35,255"/><Option name="outline_color" type="QString" value="35,95,35,0"/><Option name="outline_width" type="QString" value="0"/><Option name="style" type="QString" value="solid"/><Option name="outline_style" type="QString" value="no"/><Option name="joinstyle" type="QString" value="bevel"/></Option>
          <data_defined_properties><Option type="Map"/></data_defined_properties>
        </layer>
      </symbol>
      <symbol name="1" type="fill" clip_to_extent="1" alpha="0.7" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <Option type="Map"><Option name="color" type="QString" value="80,190,55,255"/><Option name="outline_color" type="QString" value="80,190,55,0"/><Option name="outline_width" type="QString" value="0"/><Option name="style" type="QString" value="solid"/><Option name="outline_style" type="QString" value="no"/><Option name="joinstyle" type="QString" value="bevel"/></Option>
          <data_defined_properties><Option type="Map"/></data_defined_properties>
        </layer>
      </symbol>
      <symbol name="2" type="fill" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <Option type="Map"><Option name="color" type="QString" value="0,0,0,0"/><Option name="outline_color" type="QString" value="0,0,0,0"/><Option name="outline_width" type="QString" value="0"/><Option name="style" type="QString" value="no"/><Option name="outline_style" type="QString" value="no"/><Option name="joinstyle" type="QString" value="bevel"/></Option>
          <data_defined_properties><Option type="Map"/></data_defined_properties>
        </layer>
        <layer class="LinePatternFill" enabled="1" pass="0" locked="0">
          <Option type="Map"><Option name="angle" type="QString" value="45"/><Option name="distance" type="QString" value="1.4"/><Option name="lineangle" type="QString" value="0"/><Option name="outline_width_unit" type="QString" value="MM"/></Option>
          <symbol type="line" clip_to_extent="1" alpha="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map"><Option name="line_color" type="QString" value="80,190,55,255"/><Option name="line_width" type="QString" value="0.35"/><Option name="line_width_unit" type="QString" value="MM"/><Option name="line_style" type="QString" value="solid"/><Option name="capstyle" type="QString" value="square"/><Option name="joinstyle" type="QString" value="bevel"/></Option>
              <data_defined_properties><Option type="Map"/></data_defined_properties>
            </layer>
          </symbol>
          <data_defined_properties><Option type="Map"/></data_defined_properties>
        </layer>
      </symbol>
      <symbol name="3" type="fill" clip_to_extent="1" alpha="0.7" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <Option type="Map"><Option name="color" type="QString" value="130,240,160,255"/><Option name="outline_color" type="QString" value="130,240,160,0"/><Option name="outline_width" type="QString" value="0"/><Option name="style" type="QString" value="solid"/><Option name="outline_style" type="QString" value="no"/><Option name="joinstyle" type="QString" value="bevel"/></Option>
          <data_defined_properties><Option type="Map"/></data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <source-symbol>
      <symbol name="0" type="fill" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <Option type="Map"><Option name="color" type="QString" value="190,207,80,255"/><Option name="outline_color" type="QString" value="35,35,35,255"/><Option name="outline_width" type="QString" value="0.26"/><Option name="outline_width_unit" type="QString" value="MM"/><Option name="style" type="QString" value="solid"/><Option name="outline_style" type="QString" value="solid"/><Option name="joinstyle" type="QString" value="bevel"/></Option>
          <data_defined_properties><Option type="Map"/></data_defined_properties>
        </layer>
      </symbol>
    </source-symbol>
    <colorramp type="randomcolors" name="random"><Option/></colorramp>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1"><DiagramCategory enabled="0" backgroundColor="#ffffff" opacity="1" width="15" height="15" minScaleDenominator="0" maxScaleDenominator="1e+08" scaleBasedVisibility="0" barWidth="5" lineSizeScale="3x:0,0,0,0,0,0"/></SingleCategoryDiagramRenderer>
  <DiagramLayerSettings placement="0" priority="0" zIndex="0" showAll="1" linePlacementFlags="18" obstacle="0" dist="0" xPosColumn="" yPosColumn="" showColumn="-1"/>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="scenario" configurationFlags="None"><editWidget type="TextEdit"><config><Option/></config></editWidget></field>
    <field name="typ_inond" configurationFlags="None"><editWidget type="TextEdit"><config><Option/></config></editWidget></field>
  </fieldConfiguration>
  <customproperties>
    <Option type="Map"><Option name="dualview/previewExpressions" type="List"><Option type="QString" value="&quot;scenario&quot;"/></Option></Option>
  </customproperties>
</qgis>