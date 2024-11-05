import convert from 'xml-js';

const data = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Style id="3d_polyline1">
<LineStyle>
<color>ff0000ff</color>
<width>5</width>
</LineStyle>
<PolyStyle>
<color>7f0000ff</color>
</PolyStyle>
</Style>
<Placemark>
<name>3D Polyline</name>
<styleUrl>#3d_polyline</styleUrl>
<LineString>
<altitudeMode>absolute</altitudeMode>
<coordinates>
77.19367,28.54503,100
77.19367,28.54503,119
77.19367,28.54503,129
77.19367,28.54503,139
</coordinates>
</LineString>
</Placemark>
</Document>
</kml>`;



var result = JSON.parse(convert.xml2json(data, {compact: true, spaces: 4}));
console.log(result.kml.Document.Placemark.LineString.coordinates)
