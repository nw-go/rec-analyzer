from flask import Flask, Blueprint, render_template, redirect, request, session, Response, url_for, send_from_directory
from colorama import init, Fore, Back
import socket, sys, config as cfg
from tools import AppData, get_folders, join, sizeSince, encode64, decode64, is_valid_file
from functools import wraps

init()
app = Flask(__name__, instance_relative_config=False, static_folder='.static', template_folder='.templates')
app.config.from_object('config.Config')
appData = AppData()


@app.context_processor
def inject_common_data():
    return dict(encode64=encode64, decode64=decode64, sizeSince=sizeSince, logged_in=session.get('logged_in'))

def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if session.get('logged_in'):
            return func(*args, **kwargs)
        return redirect('/login')
    return decorated_view

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if session.get('logged_in'):
        return redirect(request.args.get('next') or '/')
    if request.method == 'GET':
        error = session.get('error_login')
        if error:
            session['error_login'] = None
        return render_template('login.html', error=error)

    if appData.check_password(request.form.get('password')):
        session['logged_in'] = True
        return redirect(request.args.get('next') or '/')

    session['error_login'] = 'Incorrect username or password'
    return redirect('/login')

@app.route("/logout")
@login_required
def logout():
    session['logged_in'] = False
    return redirect('/login')

@app.route('/')
@login_required
def index_view():
    global appData
    folders = sorted(get_folders(appData.get('rec_folder')))
    return render_template('index.html', rec_names=folders, count=len(folders))

@app.route('/map/<rec_name>/')
@app.route('/map/<rec_name>/<rec_date>')
@login_required
def map_go_view(rec_name, rec_date=None):
    global appData
    rec_folder = appData.get('rec_folder')
    if not rec_name or not rec_name in get_folders(rec_folder):
        return redirect('/')
    
    all_dates = sorted(get_folders(join(rec_folder, rec_name)))

    if rec_date:
        if rec_date in all_dates:
            date_index = all_dates.index(rec_date)
            old_date, next_date = None, None
            if date_index != 0:
                old_date = all_dates[date_index-1]
            if date_index != len(all_dates) - 1:
                next_date = all_dates[date_index+1]

            all_records = appData.get_records(rec_name, rec_date)
            all_records.sort(key=lambda i: i['call_time_object'], reverse=False)

            return render_template('records.html', rec_name=rec_name, size=appData.get_files_size(all_records), records=all_records, total=len(all_records), date=rec_date, old_date=old_date, next_date=next_date)
        else:
            return redirect('/map/'+rec_name)

    return render_template('map.html', rec_name=rec_name, all_dates=all_dates, count=len(all_dates))

@app.route('/file')
def download_view():
    if not session.get('logged_in'):
        return Response(status=403)
    try:
        fl, name, date = request.args.get('fl'), request.args.get('name'), request.args.get('date')
        if fl and name and date and is_valid_file(join(appData.get('rec_folder'), name, date, fl)):
            return send_from_directory(join(appData.get('rec_folder'), name, date), fl, as_attachment=True)
    except:
        pass
    return Response(status=404)

if __name__ == "__main__":
    host = socket.gethostbyname(socket.gethostname())
    port = 1999
    if len(sys.argv) == 2:
        host = sys.argv[1]
    elif len(sys.argv) == 3:
        if sys.argv[1] != '*':
            host = sys.argv[1]
        port = int(sys.argv[2])
    elif len(sys.argv) > 3:
        print('\n[+] - Too Many Parameters')
        exit(1)

    print(f'\n\t ****  REC ANALYZER v{cfg.VERSION}  ****\n')
    print(' * Host : ', host)
    print(' * Port : ', port)
    app.run(host=host, port=port, debug=True)
