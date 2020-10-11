import geopandas as gpd
from shapely.geometry import shape, Point, LineString
from bokeh.plotting import figure, save, output_file
from bokeh.models import ColumnDataSource, GeoJSONDataSource
from bokeh.models.tools import WheelZoomTool
from bokeh.tile_providers import CARTODBPOSITRON_RETINA, get_provider
from routingpy import ORS


class Visualizer(object):
    """Visualize routes on maps
    """
    def __init__(self, list_nodes, outfp='routes_map.html'):
        # If you run the visualizer outside of docker uncomment the following line
        # self.base_url = 'http://localhost:8180/ors'
        self.base_url = 'http://host.docker.internal:8180/ors'
        self.list_nodes = list_nodes
        self.outfp = outfp

    def main(self):
        # print('Visualizing {}'.format(self.in_file))
        # Read data
        self.read_data()
        # Plot points
        self.visualize_nodes()
        # Plot route
        self.visualize_routes()
        # Save map
        # self.save_map()
        return self.p

    def read_data(self):
        geometry = [Point(xy) for xy in self.list_nodes]
        crs='EPSG:4326'
        self.gdf = gpd.GeoDataFrame(crs=crs, geometry=geometry)
        self.gdf = self.gdf.to_crs(epsg=3857)

    def visualize_nodes(self):
        # print('Creating node visualization')
        points = self.gdf.copy()
        points['x'] = points.apply(self.getPointCoords, geom='geometry', coord_type='x', axis=1)
        points['y'] = points.apply(self.getPointCoords, geom='geometry', coord_type='y', axis=1)
        p_df = points.drop('geometry', axis=1).copy()
        self.psource = ColumnDataSource(p_df)
        self.p = figure(title="Routes and locations")
        tile_provider = get_provider(CARTODBPOSITRON_RETINA)
        self.p.add_tile(tile_provider)
        self.p.circle('x', 'y', source=self.psource, size=10)

    def save_map(self):
        output_file(filename=self.outfp, title='Routes')
        save(self.p, self.outfp)

    def visualize_routes(self):
        self.routes_gdf = self.create_routes()
        self.make_route_plot()

    def create_routes(self):
        route_line = self.osrm_query(self.list_nodes)
        routes_gdf['geometry'] = [route_line]
        routes_gdf = gpd.GeoDataFrame(crs='epsg:4326')
        routes_gdf = routes_gdf.to_crs(epsg=3857)
        
        return routes_gdf

    def make_route_plot(self):
        source_shape = GeoJSONDataSource(geojson=self.routes_gdf.to_json())
        self.p.multi_line('xs', 'ys', source=source_shape, 
                            line_width=3, line_dash='dashed')
        # self.p.legend.click_policy = 'hide'
        self.p.toolbar.active_scroll = self.p.select_one(WheelZoomTool)

    def getPointCoords(self, row, geom, coord_type):
        """Calculates coordinates ('x' or 'y') of a Point geometry"""
        if coord_type == 'x':
            return row[geom].x
        elif coord_type == 'y':
            return row[geom].y

    def osrm_query(self, list_points, tries=0, max_tries=5):
        try:
            client = ORS(base_url=self.base_url)
            response = client.directions(list_points, 'driving-car', format='geojson',
                                         instructions=False,)
            response_dict = {'coordinates': response.geometry,
                             'type': 'LineString'}
            route_line = shape(response_dict)
        except:
            tries += 1
            if tries > max_tries:
                route_line = self.route_from_nodes(list_points)
            else:
                route_line = self.osrm_query(list_points, tries)
        return route_line

    def route_from_nodes(self, list_points):
        route_line = LineString(list_points)
        return route_line

if __name__ == "__main__":
    list_nodes = [(5.296621, 51.690146), (5.338494, 51.713828), (5.701922, 50.842685)]
    viz = Visualizer(list_nodes)
    viz.main()