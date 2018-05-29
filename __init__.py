#!/home/dax/virtualenvs/scpy/bin/ipython	
from flask import Flask, jsonify, render_template, request,Response, g
from flaskext.mysql import MySQL
from functools import wraps
import json
import MySQLdb
import operator
app = Flask(__name__)

from credentials import *

@app.before_request
def db_connect():
    g.db_conn = MySQLdb.connect(host=DB_HOST,
                                user=DB_USER,
                                passwd=DB_PASSWD)

@app.teardown_request
def db_disconnect(exception=None):
    g.db_conn.close()

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'dax' and password == 'peachlab'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/project')
def project():
    return render_template('project.html')

@app.route('/proj_db_man')
def list_db():
    return render_template('proj_db_man.html')


@app.route('/slow_control')
def slow_control():
    return render_template('sl_plots_select.html')

@app.route('/slow_control_move')
def slow_control_move():
    return render_template('sl_plots_select.html')

@app.route('/slow_control_datetime')
def slow_control_datetime():
    return render_template('sl_datepick.html')


@app.route('/get_db')
def get_db():
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    query = """
            show tables
            """
    cursor.execute(query)
    return jsonify({'data':cursor.fetchall()})

@app.route('/table_info', methods=['GET','POST'])
def table_info():
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    table_name = request.form['table'];
    query = """
            describe %s
            """ % (table_name)
    cursor.execute(query)
    result = cursor.fetchall()
    print result
    return jsonify({'data':result})


@app.route('/read_proj')
def read_proj():
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    
    query = """
            select * from items
            """
    cursor.execute(query)
    result = cursor.fetchall()

    return jsonify({'data':result})

@app.route('/read_links')
def read_links():
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    
    query = """
            select source,target,cable_type from links
            """
    cursor.execute(query)
    result = cursor.fetchall()

    return jsonify({'data':result})

@app.route('/project_adding_page')
@requires_auth
def project_adding_page():
    return render_template('project_adding_page.html')

@app.route('/project_reading_page')
def project_reading_page():
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    
    query = """
            select * from items
            """
    cursor.execute(query)
    result = cursor.fetchall()
    name = [x[0] for x in result]
    shortname = [x[1] for x in result]
    completed = [x[2] for x in result]
    remaining = [x[3] for x in result]
    owners = [x[4] for x in result]
 
    return render_template('project_reading_page.html',items=zip(name,shortname,owners,completed,remaining))


@app.route('/link_reading_page')
def link_reading_page():
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()

    cursor.execute("SELECT name,shortname FROM items INNER JOIN links on links.source = items.shortname")
    result = cursor.fetchall()
    sources_long = [x[0] for x in result]
    sources_short_items = [x[1] for x in result]
    cursor.execute("SELECT name,shortname FROM items INNER JOIN links on links.target = items.shortname")
    result = cursor.fetchall()
    targets_long = [x[0] for x in result]
    targets_short_items = [x[1] for x in result]

    item_source_dict = dict()
    item_target_dict = dict()
    for sl,ss,tl,ts in zip(sources_long,sources_short_items,targets_long,targets_short_items):
        item_source_dict[ss] = sl
        item_target_dict[ts] = tl


    cursor.execute("SELECT name,shortname FROM items")
    result = cursor.fetchall()
    names = [x[0] for x in result]
    shortnames = [x[1] for x in result]


    cursor.execute("SELECT * FROM links")
    result = cursor.fetchall()
    sources_long = [item_source_dict[x[0]] for x in result]
    targets_long  = [item_target_dict[x[1]] for x in result]
    cable_types = [x[2] for x in result]
    primary_key = [x[3] for x in result]


    return render_template('link_reading_page.html',names=zip(names,shortnames),links=zip(sources_long,targets_long,cable_types,primary_key))


@app.route('/project_edit_page', methods=['GET','POST'])
@requires_auth
def project_edit_page():
    shortname = request.form['items'];
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    if request.form['submit'] == "modify":
        cursor.execute("SELECT * FROM items WHERE shortname LIKE %s", [shortname])
        result = cursor.fetchall()
        name = result[0][0]
        shortname = result[0][1]
        complete = result[0][2]
        remaining = result[0][3]
        owners = result[0][4]
        if not owners:
            owners = "None"

        return render_template('project_edit_page.html',name=name,shortname=shortname,status_complete=complete,status_remaining=remaining,owners=owners)

    elif request.form['submit'] == "delete":
        cursor.execute("DELETE FROM items WHERE shortname = %s", [shortname])
        return project_reading_page()

@app.route('/create_link', methods=['POST'])
@requires_auth
def create_link():

    source =  request.form['source'];
    target = request.form['target'];
    cable_type = request.form['cable_type'];
    
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    cursor.execute("INSERT INTO links (source,target,cable_type) VALUES (%s,%s,%s)", (source,target,cable_type))
    g.db_conn.commit()
 
    return link_reading_page()

@app.route('/delete_link', methods=['POST'])
@requires_auth
def delete_link():

    primary_key =  int(request.form['links']);

    
    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    cursor.execute("DELETE FROM links WHERE id = %d" %(primary_key))
    g.db_conn.commit()
    
    return link_reading_page()

@app.route('/add_proj', methods=['POST'])
@requires_auth
def add_proj():

    name =  request.form['name'];
    shortname = request.form['shortname'];
    status_complete = request.form['status_complete'];
    status_remaining = request.form['status_remaining'];
    owners = request.form['owners'];
    if not status_complete:
        status_complete = "To be determined"
    if not status_remaining:
        status_remaining = "To be determined"
    if not owners:
        owners = "None"

    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    cursor.execute("INSERT INTO items VALUES (%s,%s,%s,%s,%s)", (name,shortname,status_complete,status_remaining,owners))
    g.db_conn.commit()
    return render_template('proj_db_man.html')

@app.route('/edit_proj', methods=['POST'])
@requires_auth
def edit_proj():

    name =  request.form['name']
    shortname = request.form['shortname']
    status_complete = request.form['status_complete']
    status_remaining = request.form['status_remaining']
    oldshortname = request.form['oldshortname']
    owners = request.form['owners']
    if not status_complete:
        status_complete = "To be determined"
    if not status_remaining:
        status_remaining = "To be determined"
    if not owners:
        owners = "None"

    g.db_conn.select_db(PROJ_DB_NAME)
    cursor = g.db_conn.cursor()
    cursor.execute("UPDATE items SET name = %s, shortname = %s, status_complete = %s, status_remaining = %s, owners = %s WHERE shortname = %s", (name,shortname,status_complete,status_remaining,owners,oldshortname))
    #cursor.execute("INSERT INTO items VALUES (%s,%s,%s,%s)", (name,shortname,status_complete,status_remaining))
    g.db_conn.commit()
    return project_reading_page()




@app.route('/slow_control_plotting', methods=['GET'])
def user_classification():
    g.db_conn.select_db(DAX_DB_NAME)
    cursor = g.db_conn.cursor()
    tables = {'CAP1':'CapacitanceUNITpf','VAC2':'Pressure2UNITkpa','MFC1':'FlowUNITsccm','TMPA':'TemperatureAUNITK','STR':'Strain2UNITkg','TMPB':'TemperatureBUNITK','VAC1':'PressureUNITtorr'}
    tmp_table = None
    results_dict = dict()
    for table in tables:
	var_to_get = tables[table]
	if table is 'TMPA' or table is 'TMPB':
		tmp_table = table
		table = 'TMP'
	query = """
                select 1000*TimeUNITS,%s from %s
                where TimeUNITs < unix_timestamp(current_timestamp()) and TimeUNITs > unix_timestamp(current_timestamp())-86400 
		and %s != -9999999
                order by TimeUNITs desc
                """ % (var_to_get,table,var_to_get)
        cursor.execute(query)
	if tmp_table:
		table=tmp_table
	tmp_table = None
        results_dict[table] = cursor.fetchall()[::-1]
    
    return jsonify(results_dict)


@app.route('/slow_control_data', methods=['GET','POST'])
def slow_control_data():
    g.db_conn.select_db(DAX_DB_NAME)
    cursor = g.db_conn.cursor()
    table = str(request.get_json()['table'])
    last_time = float(request.get_json()['last_time'])
    if last_time == 0:
        lower_cut = "unix_timestamp(current_timestamp())-86400"
    else:
        lower_cut = "%f"%last_time
    tables = {'CAP1':'CapacitanceUNITpf','VAC2':'Pressure2UNITkpa','MFC1':'FlowUNITsccm','TMPA':'TemperatureAUNITK','STR':'Strain2UNITkg','TMPB':'TemperatureBUNITK','VAC1':'PressureUNITtorr','TMP':'HeaterPowerUNITPercentage'}
    tmp_table = None
    results_dict = dict()
    var_to_get = tables[table]
    if table == 'TMPA' or table == 'TMPB':
        tmp_table = table
        table = 'TMP'
    query = """
            select 1000*TimeUNITS,%s from %s
            where TimeUNITs < unix_timestamp(current_timestamp()) and TimeUNITs > %s
            and %s != -9999999
            order by TimeUNITs desc
            """ % (var_to_get,table,lower_cut,var_to_get)
    cursor.execute(query)
    if tmp_table:
            table=tmp_table
    tmp_table = None
    results_dict[table] = cursor.fetchall()[::-1]

    return jsonify(results_dict)

@app.route('/slow_control_data_time_selection', methods=['GET','POST'])
def slow_control_data_time_selection():
    g.db_conn.select_db(DAX_DB_NAME)
    cursor = g.db_conn.cursor()
    table = str(request.get_json()['table'])
    start_time = float(request.get_json()['start_time'])
    stop_time = float(request.get_json()['stop_time'])
    tables = {'CAP1':'CapacitanceUNITpf','VAC2':'Pressure2UNITkpa','MFC1':'FlowUNITsccm','TMPA':'TemperatureAUNITK','STR':'Strain2UNITkg','TMPB':'TemperatureBUNITK','VAC1':'PressureUNITtorr','TMP':'HeaterPowerUNITPercentage'}
    tmp_table = None
    results_dict = dict()
    var_to_get = tables[table]
    if table == 'TMPA' or table == 'TMPB':
        tmp_table = table
        table = 'TMP'
    query = """
            select 1000*TimeUNITS,%s from %s
            where TimeUNITs < %s and TimeUNITs > %s
            order by TimeUNITs desc
            """ % (var_to_get,table,stop_time,start_time)
    cursor.execute(query)
    if tmp_table:
            table=tmp_table
    tmp_table = None
    results_dict[table] = cursor.fetchall()[::-1]

    return jsonify(results_dict)


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=80)
