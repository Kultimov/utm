import json
import os
from sqlite3 import OperationalError
from glob import glob

from flask import Flask, request
from gtfspy import gtfs
from gtfspy import stats
from flask_runner import Runner


import settings
from flask_cors import CORS, cross_origin

if __name__ == '__main__':
    DEBUG = True
else:
    BASE_URL = '/transit/'


app = Flask(__name__, static_url_path='')
CORS(app)
app.config.from_object(__name__)

@app.route("/")
@app.route("/dummy2")
def index():
    return json.dumps({"url": str(request.url), "query_string": str(request.query_string)})

if not __name__ == '__main__':
    # If in production: add a logging handler
    import logging
    from logging import FileHandler
    file_handler = FileHandler('log/log.txt')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

viz_cache = {}

def cache(func, *args, **kwargs):
    name = func.func_name
    args_ = hash(tuple(args))
    kwargs_ = hash(tuple(kwargs.items()))
    cache_key = (name, args_, kwargs_)
    if cache_key not in viz_cache:
        viz_cache[cache_key] = func(*args, **kwargs)
    else:
        print("found in cache")
    return viz_cache[cache_key]

def find_dbfnames():
    dbfnames = []
    for sdir in settings.DB_DIRS:
        # If is a regular file, just use this directly.
        if os.path.isfile(sdir):
            dbfnames.append(sdir)
            continue
        # Directories: all sub-directory sqlite files.
        for cur_dir, subdirs, files in os.walk(sdir):
            for ending in settings.DB_ENDINGS:
                dbfnames.extend(glob(os.path.join(cur_dir, ending)))
    dbfnames = list(set(dbfnames)) # remove any duplicates
    # Remove common prefix
    if len(dbfnames) == 1:
        commonprefix = ""
    else:
        commonprefix = os.path.commonprefix(dbfnames)
        dbfnames = [fname[len(commonprefix):] for fname in dbfnames]
    # exclude tests:
    dbfnames = sorted([e for e in dbfnames if "proc/test/" not in e])
    valid_dbfnames = []
    timezone_dict = {}
    for dbf in dbfnames:
        try:
            timezone_dict[dbf] = gtfs.GTFS(commonprefix+dbf).get_timezone_string()
            valid_dbfnames.append(dbf)
        except OperationalError as e:
            print("database " + dbf + " is not available due to: \n" + e.message)

    data = {'dbfnames': valid_dbfnames,
            'timezones': timezone_dict}
    dbfname_cache = json.dumps(data)
    return dbfnames, commonprefix, dbfname_cache

# Run finder function to set the needed variables.
dbfnames, commonprefix, dbfname_cache = find_dbfnames()

def get_dbfname(dbfname):
    if dbfname not in dbfnames:
        return None
    return commonprefix + dbfname

@app.route("/databases")
def available_gtfs_dbs():
    return dbfname_cache

@app.route("/trajectories")
def get_scheduled_trips_within_interval():
    tstart = request.args.get('tstart', None)
    tend = request.args.get('tend', None)
    dbfname = get_dbfname(request.args.get('dbfname', None))
    shapes = request.args.get('use_shapes', None)

    if shapes == "1":
        shapes = True
    else:
        shapes = False
    if tstart:
        tstart = int(tstart)
    if tend:
        tend = int(tend)

    G = gtfs.GTFS(dbfname)

    trips = G.get_trip_trajectories_within_timespan(start=tstart, end=tend, use_shapes=False)
    return json.dumps(trips)

@app.route("/stats")
def get_gtfs_stats():
    dbfname = get_dbfname(request.args.get('dbfname', None))
    if not dbfname:
        return json.dumps({})
    G = gtfs.GTFS(dbfname)
    data = stats.get_stats(G)
    return json.dumps(data)


@app.route("/gtfsspan")
def get_start_and_end_time_ut():
    dbfname = get_dbfname(request.args.get('dbfname', ""))
    if dbfname is "null":
        dbfname = ""
    G = gtfs.GTFS(dbfname)
    start, end = G.get_approximate_schedule_time_span_in_ut()
    data = {
        "start_time_ut": start,
        "end_time_ut": end
    }
    return json.dumps(data)

@app.route("/tripsperday")
def get_trip_counts_per_day():
    dbfname = get_dbfname(request.args.get('dbfname', None))
    if not dbfname:
        return json.dumps({})
    g = gtfs.GTFS(dbfname)
    data = g.get_trip_counts_per_day()
    data_dict = {
        "trip_counts": [int(c) for c in data["trip_counts"].values],
        "dates": [str(date) for date in data["date_str"].values]
    }
    return json.dumps(data_dict)


@app.route("/stopcounts")
def view_stop_data():
    #print request.args
    tstart = int(request.args.get('tstart', None))
    tend = int(request.args.get('tend', None))
    dbfname = get_dbfname(request.args.get('dbfname', None))
    G = gtfs.GTFS(dbfname)  # handles connections to database etc.
    stopdata = G.get_stop_count_data(tstart, tend)
    return stopdata.to_json(orient="records")
    # json.dumps(stopdata.to_dict("records"))


@app.route("/linkcounts")
def view_segment_data():
    #print request.args
    tstart = int(request.args.get('tstart', None))
    tend = int(request.args.get('tend', None))
    dbfname = get_dbfname(request.args.get('dbfname', None))
    shapes = request.args.get('use_shapes', None)
    if shapes == "1":
        shapes = True
    else:
        shapes = False
    G = gtfs.GTFS(dbfname)  # handles connections to database etc.
    data = G.get_segment_count_data(tstart, tend, use_shapes=shapes)
    return json.dumps(data)


@app.route("/routes")
def view_line_data():
    #print request.args
    dbfname = get_dbfname(request.args.get('dbfname', None))
    shapes = request.args.get('use_shapes', None)
    if shapes == "1":
        shapes = True
    else:
        shapes = False
    G = gtfs.GTFS(dbfname)  # handles connections to database etc.
    data = G.get_all_route_shapes(use_shapes=shapes)

    routes = []
    for raw_route in data:
        agency = raw_route["agency"]
        lats = [float(lat) for lat in raw_route['lats']]
        lons = [float(lon) for lon in raw_route['lons']]
        route_type = int(raw_route['type'])
        name = str(raw_route['name'])
        agency_name = str(raw_route['agency_name'])
        route = {
            "agency": agency,
            "lats": lats,
            "lons": lons,
            "route_type": route_type,
            "name": name,
            "agency_name": agency_name
        }
        routes.append(route)
    return json.dumps(routes)


@app.route("/spreading")
def view_spreading_explorer():
    dbfname = get_dbfname(request.args.get('dbfname', None))
    shapes = request.args.get('use_shapes', None)
    tstart = request.args.get('tstart', None)
    tend = request.args.get('tend', None)
    lat = request.args.get('lat', None)
    lon = request.args.get('lon', None)
    if not dbfname:
        return json.dumps({})
    if tstart:
        tstart = int(tstart)
    if tend:
        tend = int(tend)
    if lat:
        lat = float(lat)
    if lon:
        lon = float(lon)
    if shapes == "1":
        shapes = True
    else:
        shapes = False
    G = gtfs.GTFS(dbfname)
    data = G.get_spreading_trips(tstart, lat, lon, tend - tstart, use_shapes=shapes)
    return json.dumps(data)


application = app

if __name__ == "__main__":
    runner = Runner(app)
    runner.run()


