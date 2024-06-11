from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import requests
from datetime import datetime
from logging import getLogger

app = Flask(__name__)
app.secret_key = 'uxRGCtkSMp0SogIhvIkQwtd8wkZGZ9HH'
lg = getLogger("")

@app.context_processor
def inject_user():
    return dict(username=session.get('username', None))

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        url = "http://0.0.0.0:8000/token"
        data = {
            "username": username,
            "password": password,
            'scope'   : ["me"]
        }
        resp = requests.post(url=url, data=data)

        if resp.status_code == 200 :
            token = resp.json()
            if "access_token" in token :
                token = f"{token['token_type'].capitalize()} {token['access_token']}"
                session['username'] = username
                session['token'] = token
                return redirect(url_for('index'))
            else :
                flash(f"Fail to authenticate : {resp.reason}")
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('token', None)
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat(**kwargs):
    if not 'username' in session:
        return redirect(url_for('login'))
    
    user_input  = request.form.get('user_input', None)
    print(f'user input : {user_input}')
    task_id     = request.form.get('task_id', None)
    print(f'task_id : {task_id}')
    
    if task_id :
        url = f"http://0.0.0.0:8000/tasks/{task_id}"
        resp = requests.get(url=url, data=data)
        if resp.status_code ==200 :
            resp_data = resp.json()
            response_dict = {
                'status' : resp_data['status'],
                'result' : resp_data['result']['generated_paragraphs']
            }
            return jsonify({'response': response_dict})
        elif resp.status_code ==202 :
            resp_data = resp.json()
            response_dict = {
                'status' : resp_data['status'],
                'result' : None
            }
            return jsonify({'response': response_dict})
        else:
            response_dict = {
                'status' : 'ERROR'
            }
            return jsonify({'response': response_dict})

    elif user_input :
        url = "http://0.0.0.0:8000/users/me/search/"
        data = {
            "search_platform": "google_scholar",
            "prompt": user_input,
            "search_type": "web"
            }
        resp = requests.post(url=url, data=data)
        print(resp.status_code)
        if resp.status_code == 202:
            resp_data = resp.json()
            response_dict = {
                'task_id' : resp_data['id']
            }
            return jsonify({'response': response_dict})
        
        elif resp.status_code == 401 :
            return jsonify({'response': 'token_invalid'})
        
        else :
            return jsonify({'response': "error"})
    else :
        return jsonify({'response': "invalid request"})
    


    # response = requests.post(MODEL_API_URL, json={'input': user_input})
    # response_text = response.json().get('response', 'No response from model')
    # return jsonify({'response': response_text})

@app.route('/history')
def history():
    if not 'username' in session:
        return redirect(url_for('login'))
    
    url = "http://0.0.0.0:8000/users/me/searches/"
    headers = {"Authorization": session['token']}
    resp = requests.get(url=url
                        , headers=headers
                        , params= {
                            'skip' : 0,
                            'limit': 5
                        })
    # except Exception as e:
    #     e_text = f"Fail to retrieve searches for user"
    #     lg.error(e_text, exc_info=True)
    #     raise ConnectionError(e_text) from e
    
    if resp.status_code == 200 :
        search_list = list()
        resp_data = resp.json()
        if resp_data :
            for search in resp_data:
                search_list.append({
                    'date'      :   datetime.fromisoformat(search['date_of_search']).strftime("%d/%m/%Y at %H:%M"),
                    'id'        :   search['id'],
                    'plateform' :   search['search_platform'],
                    'type'      :   search['search_type']
                })
            return render_template('history.html', searches=search_list)   
        return render_template('history.html', searches=None)
    elif resp.status_code == 404:
        return render_template('history.html', searches=None)
    else :
        return render_template('history.html', error=True, reason=resp.reason)

@app.route('/search', methods=['GET', 'POST'])
def search(**kwargs):
    if not 'username' in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_input = request.form.get('user_input', None)
        if user_input :
            return render_template('search/search_result.html', user_input=user_input)
    if kwargs.get('search_id', None):
        url = f"http://0.0.0.0:8000/users/me/searches/{kwargs['search_id']}"
        resp = requests.get(url=url)
        
        if resp.status_code ==200 :
            resp_data = resp.json()
            response_out = {
                "paragraphs"    : resp_data['result']['generated_paragraphs'],
                "id"            : kwargs['search_id']
                }
            return render_template('search/search_result.html', search_data=response_out)
    

    return render_template("search/search_prompt.html")

# @app.route('/search_result')
# def search_result(**kwargs):
#     return render_template('search/search_result.html', **kwargs)

if __name__ == '__main__':
    app.run(debug=True)
