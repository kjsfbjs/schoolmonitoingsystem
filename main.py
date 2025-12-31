from flask import Flask, render_template_string, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "schoolappsecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///school_system.db"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)
db = SQLAlchemy(app)

# ================= DATABASE =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    grade = db.Column(db.String(20))
    marks = db.Column(db.Integer)
    marksheet = db.Column(db.String(200))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin",
                     password=generate_password_hash("admin"),
                     role="admin")
        db.session.add(admin)
        db.session.commit()

# ================= HELPERS =================
def require_login():
    if "user" not in session:
        return redirect("/")

def require_admin():
    if "user" not in session or session["role"] != "admin":
        return redirect("/dashboard")

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    error = ""
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        u = User.query.filter_by(username=username).first()
        if u and check_password_hash(u.password,password):
            session["user"]=u.username
            session["role"]=u.role
            return redirect("/dashboard")
        else:
            error="Invalid credentials"
    return render_template_string(login_html,error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    r = require_login()
    if r: return r
    total_students = Student.query.count()
    return render_template_string(dashboard_html,total=total_students,role=session["role"])

# ================= USER MANAGEMENT =================
@app.route("/users", methods=["GET","POST"])
def users():
    r = require_admin()
    if r: return r
    msg=""
    if request.method=="POST":
        if "add_user" in request.form:
            u = request.form["username"]
            p = request.form["password"]
            role = request.form["role"]
            if User.query.filter_by(username=u).first():
                msg="User already exists!"
            else:
                user = User(username=u,password=generate_password_hash(p),role=role)
                db.session.add(user)
                db.session.commit()
                msg="User created!"
        if "delete_user" in request.form:
            uid = request.form["delete_user"]
            user = User.query.get(uid)
            if user and user.username!="admin":
                db.session.delete(user)
                db.session.commit()
                msg="User deleted!"
    return render_template_string(users_html,users=User.query.all(),msg=msg)

# ================= ADD STUDENT =================
@app.route("/add_student", methods=["GET","POST"])
def add_student():
    r = require_login()
    if r: return r
    msg=""
    if request.method=="POST":
        name=request.form["name"]
        address=request.form["address"]
        phone=request.form["phone"]
        grade=request.form["grade"]
        marks=request.form["marks"]
        student=Student(name=name,address=address,phone=phone,grade=grade,marks=marks,marksheet="")
        db.session.add(student)
        db.session.commit()
        msg="Student added!"
    return render_template_string(add_student_html,msg=msg)

# ================= MANAGE STUDENTS =================
@app.route("/students", methods=["GET","POST"])
def students():
    r=require_login()
    if r: return r
    msg=""
    if request.method=="POST":
        if "delete" in request.form:
            sid=request.form["delete"]
            s=Student.query.get(sid)
            db.session.delete(s)
            db.session.commit()
            msg="Deleted!"
        if "update" in request.form:
            sid=request.form["sid"]
            s=Student.query.get(sid)
            s.name=request.form["name"]
            s.address=request.form["address"]
            s.phone=request.form["phone"]
            s.grade=request.form["grade"]
            s.marks=request.form["marks"]
            file=request.files["pdf"]
            if file.filename:
                filename=secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"],filename))
                s.marksheet=filename
            db.session.commit()
            msg="Updated!"
    all_students=Student.query.all()
    return render_template_string(manage_html,students=all_students,msg=msg)

# ================= IMPORT =================
@app.route("/import",methods=["GET","POST"])
def import_excel():
    r=require_admin()
    if r: return r
    msg=""
    if request.method=="POST":
        file=request.files["excel"]
        df=pd.read_excel(file)
        for _,row in df.iterrows():
            s=Student(name=row["name"],address=row["address"],phone=row["phone"],
                      grade=row["grade"],marks=row["marks"],marksheet=row["marksheet"])
            db.session.add(s)
        db.session.commit()
        msg="Imported!"
    return render_template_string(import_html,msg=msg)

# ================= EXPORT =================
@app.route("/export")
def export_excel():
    r=require_login()
    if r: return r
    students=Student.query.all()
    data=[{"Name":s.name,"Address":s.address,"Phone":s.phone,"Grade":s.grade,"Marks":s.marks,"Marksheet":s.marksheet} for s in students]
    df=pd.DataFrame(data)
    path="students_export.xlsx"
    df.to_excel(path,index=False)
    return send_file(path,as_attachment=True)

# ================= TEMPLATES =================
login_html="""
<!doctype html>
<html><head>
<title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#0d1117;color:white;display:flex;justify-content:center;align-items:center;height:100vh}.box{background:#161b22;padding:30px;border-radius:10px;width:400px}</style>
</head>
<body>
<div class="box">
<h3 class="text-center">School Login</h3>
<p style="color:red">{{error}}</p>
<form method="POST">
<input class="form-control mb-2" name="username" placeholder="Username" required>
<input class="form-control mb-2" name="password" type="password" placeholder="Password" required>
<button class="btn btn-primary w-100">Login</button>
</form>
</div>
</body></html>
"""

dashboard_html="""
<!doctype html>
<html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#0d1117;color:white}.sidebar{width:220px;position:fixed;height:100%;background:#161b22;padding:20px}.content{margin-left:240px;padding:20px} a{text-decoration:none;color:#58a6ff} a:hover{color:white}</style></head>
<body>
<div class="sidebar">
<h3>Panel</h3>
<a href="/dashboard">Dashboard</a><br><br>
<a href="/add_student">Add Student</a><br><br>
<a href="/students">Manage Students</a><br><br>
{% if role=='admin' %}
<a href="/users">Manage Users</a><br><br>
<a href="/import">Import Excel</a><br><br>
{% endif %}
<a href="/export">Export Excel</a><br><br>
<a href="/logout">Logout</a>
</div>
<div class="content">
<h2>Dashboard</h2>
<div class="card p-3 mb-2">Total Students: {{total}}</div>
</div>
</body></html>
"""

users_html="""
<!doctype html>
<html><head><title>Users</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#0d1117;color:white}</style></head><body>
<h2>Manage Users</h2>
<p>{{msg}}</p>
<form method="POST">
<input class="form-control mb-1" name="username" placeholder="Username" required>
<input class="form-control mb-1" name="password" placeholder="Password" required>
<select class="form-control mb-1" name="role"><option>admin</option><option>teacher</option><option>student</option></select>
<button class="btn btn-primary" name="add_user">Add User</button>
</form>
<table class="table table-dark table-striped">
<tr><th>ID</th><th>Username</th><th>Role</th><th>Action</th></tr>
{% for u in users %}
<tr><td>{{u.id}}</td><td>{{u.username}}</td><td>{{u.role}}</td>
<td><form method="POST"><button class="btn btn-danger" name="delete_user" value="{{u.id}}">Delete</button></form></td>
</tr>{% endfor %}
</table>
<a class="btn btn-secondary" href="/dashboard">Back</a>
</body></html>
"""

add_student_html="""
<!doctype html>
<html><head><title>Add Student</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body style="background:#0d1117;color:white">
<h2>Add Student</h2><p>{{msg}}</p>
<form method="POST">
<input class="form-control mb-1" name="name" placeholder="Name" required>
<input class="form-control mb-1" name="address" placeholder="Address" required>
<input class="form-control mb-1" name="phone" placeholder="Phone" required>
<input class="form-control mb-1" name="grade" placeholder="Grade" required>
<input class="form-control mb-1" name="marks" placeholder="Marks" required>
<button class="btn btn-primary">Add</button>
</form>
<a class="btn btn-secondary" href="/dashboard">Back</a>
</body></html>
"""

manage_html="""
<!doctype html>
<html><head><title>Manage Students</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body style="background:#0d1117;color:white">
<h2>Manage Students</h2><p>{{msg}}</p>
<table class="table table-dark table-striped">
<tr><th>ID</th><th>Name</th><th>Address</th><th>Phone</th><th>Grade</th><th>Marks</th><th>Marksheet</th><th>Actions</th></tr>
{% for s in students %}
<tr>
<td>{{s.id}}</td><td>{{s.name}}</td><td>{{s.address}}</td><td>{{s.phone}}</td><td>{{s.grade}}</td><td>{{s.marks}}</td><td>{{s.marksheet}}</td>
<td>
<form method="POST" enctype="multipart/form-data">
<input type="hidden" name="sid" value="{{s.id}}">
<input class="form-control mb-1" name="name" value="{{s.name}}">
<input class="form-control mb-1" name="address" value="{{s.address}}">
<input class="form-control mb-1" name="phone" value="{{s.phone}}">
<input class="form-control mb-1" name="grade" value="{{s.grade}}">
<input class="form-control mb-1" name="marks" value="{{s.marks}}">
<input type="file" class="form-control mb-1" name="pdf">
<button class="btn btn-primary" name="update" value="1">Update</button>
</form>
<form method="POST">
<button class="btn btn-danger" name="delete" value="{{s.id}}">Delete</button>
</form>
</td>
</tr>
{% endfor %}
</table>
<a class="btn btn-secondary" href="/dashboard">Back</a>
</body></html>
"""

import_html="""
<!doctype html>
<html><head><title>Import Excel</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body style="background:#0d1117;color:white">
<h2>Import Excel</h2><p>{{msg}}</p>
<form method="POST" enctype="multipart/form-data">
<input type="file" class="form-control mb-2" name="excel" required>
<button class="btn btn-primary">Upload</button>
</form>
<a class="btn btn-secondary" href="/dashboard">Back</a>
</body></html>
"""

if __name__=="__main__":
    app.run(debug=True)
