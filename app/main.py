from flask import Flask, request, render_template, make_response, send_file, send_from_directory
from datetime import date
import pandas as pd
import glob
import zipfile
import os
import re
from io import BytesIO


app = Flask(__name__)
today_date = str(date.today())
path = 'data/COMMENTS/'
csv_path = ''


def check_col_dict(string):
    col_dict = {
        'hr': 'HR_Name',
        'job': 'Job_Name',
        'cv': 'CV_Name',
        'feedback': 'Feedback',
        'date': 'Date',
        'job_id': 'Job_ID',
        'cv_id': 'CV_ID'
    }
    return string if string in col_dict.values() else col_dict.get(string, '')


def read_data():
    try:
        if os.path.isfile(csv_path + 'data.csv'):
            return pd.read_csv(csv_path + 'data.csv', encoding='utf-8-sig', dtype=str)
        else:
            return pd.DataFrame(columns=['HR_Name', 'Job_ID', 'Job_Name', 'CV_ID', 'CV_Name', 'Feedback', 'Date'])
    except IOError:
        return make_response('Read/create data failed.', 404)


def write_data(df, operation):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        if not os.path.exists(csv_path):
            os.makedirs(csv_path)
        df.to_csv(csv_path + 'data.csv', encoding='utf-8-sig', index=False)
        df.to_csv(csv_path + f'{today_date}.csv', encoding='utf-8-sig', index=False)
        return f'{operation} successfully.'
    except IOError:
        return make_response(f'{operation} failed.', 404)


def render_page(region=''):
    df = read_data()
    df_view = df
    filter_dict = {}
    for parameter in request.args.keys():
        filter_col = check_col_dict(parameter)
        if filter_col:
            filter_dict[filter_col] = request.args.getlist(parameter)
    hr_list = filter_dict.get('HR_Name', [])
    for key, value in filter_dict.items():
        if key == 'HR_Name':
            df = df[df[key].isin(value)]
        else:
            df = df[df[key].isin(value)]
            df_view = df_view[df_view[key].isin(value)]
    # if any of the input exist in a row of the dataframe
    # df.isin(filter_dict).all(axis=1).any()
    sort_by = check_col_dict(request.args.get('by', ''))
    if sort_by:
        df_view = df_view.sort_values(by=sort_by)
    data = df_view.to_dict('index')
    filters = {column: [*df_view[column].unique()] for column in df_view.columns}
    is_exist = {}
    if df.empty:
        is_exist = {col: col in filter_dict.keys() for col in ['HR_Name', 'Job_Name', 'Job_ID', 'CV_Name', 'CV_ID']}
        if all(is_exist.values()):
            input_data = [dict(zip(filter_dict, filter_col_values)) for filter_col_values in zip(*filter_dict.values())]
            # insert_view = '&'.join([f'{x}={input_data[0][x]}' for x in [
            #     check_col_dict(argument) for argument in request.args.getlist('insert_view')]
            #                         if x not in ['Date', 'Feedback']])
            return render_template("form.html", data=input_data, new=True, date=today_date, hr_list=hr_list,
                                   region=region)
    missing = [key for key, value in is_exist.items() if not value]
    return render_template("form.html", filter=filter_dict, sort_by=sort_by, data=data, hr_list=hr_list,
                           filters=filters, region=region, missing=missing)


@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    global csv_path
    csv_path = path
    return render_page()


@app.route('/<string:input_region>/')
def index_region(input_region):
    global csv_path
    csv_path = path + input_region + '/'
    return render_page(input_region)


@app.route('/update', methods=['POST'])
def update():
    df = read_data()
    for key, value in request.form.items():
        df.iloc[int(key)]['Feedback'] = value
        df.iloc[int(key)]['Date'] = today_date
    return write_data(df, 'Update')


@app.route('/delete', methods=['POST'])
def delete():
    df = read_data().drop([int(key) for key in request.form.keys()])
    return write_data(df, 'Delete')


@app.route('/insert', methods=['POST'])
def insert():
    df = read_data()
    df = df.append(request.json, ignore_index=True)
    return write_data(df, 'Insert')


@app.route('/download')
def download():
    df = read_data()
    hr_list = request.args.getlist('hr')
    if hr_list:
        df = df[df['HR_Name'].isin(hr_list)]
    resp = make_response(df.to_csv(encoding='utf-8-sig', index=False))
    resp.headers["Content-Disposition"] = f"attachment; filename=HR_Feedback_{today_date}.csv"
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return resp


@app.route('/files/<string:cv_id>')
def download_zip(cv_id):
    cv_files = glob.glob(f'data/CVs/*{cv_id}*.*')
    if cv_files:
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for file in cv_files:
                zf.write(file, os.path.basename(file))
        memory_file.seek(0)
        return send_file(memory_file, mimetype='zip', attachment_filename=f'{cv_id}.zip', as_attachment=True)
    return make_response(f'No files found.', 404)


@app.route('/CV/<string:cv_id>')
def download_resume(cv_id):
    cv_files = glob.glob(f'data/CVs/*{cv_id}*.*')
    if cv_files:
        if len(cv_files) > 1:
            re_cv = re.compile(r'cv|resume|c\.v|c\.v\.|résumé|lebenslauf|简历', flags=re.IGNORECASE)
            cv_files = [*filter(lambda x: re_cv.search(os.path.basename(x)), cv_files)]
        if len(cv_files) > 1:
            cv_files = [*filter(lambda x: 'pdf' in x, cv_files)]
        if len(cv_files) == 1:
            return send_file(cv_files[0])
        else:
            return make_response(f'Multiple resume/cv files are found, please download zip instead.', 404)
    return make_response(f'No resume/default file found.', 404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
