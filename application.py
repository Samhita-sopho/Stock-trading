from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    usersstock=db.execute("SELECT * FROM stocks WHERE id=:loggedin",loggedin=session["user_id"])
    stockworth=0.0
    for user in usersstock:
        stocklist=lookup(user["stocksym"])
        stockworth+=stocklist["price"]*int(user["shares"])
        db.execute("UPDATE stocks SET value=:updated where id=:id and stocksym=:sym",updated=stocklist["price"],id=session["user_id"],sym=stocklist["symbol"])
    
    row=db.execute("SELECT cash FROM users WHERE id=:loggedin",loggedin=session["user_id"])
    usersstock=db.execute("SELECT * FROM stocks WHERE id=:loggedin",loggedin=session["user_id"])
    return render_template("index.html",total=round(float(row[0]["cash"])+stockworth,2),boughtstocks=usersstock,cash="{0:.2f}".format(round(float(row[0]["cash"]),2)),flag=1)
    
    
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method=="POST":
        if bool(request.form.get("stockname",False))!=False and bool(request.form.get("shares",False))!=False :
            if request.form.get("shares").isdigit():
                stocklist=lookup(request.form.get("stockname"))
                if stocklist: 
                
                    total=stocklist["price"]*int(request.form.get("shares"))
                    row=db.execute("SELECT cash FROM users where id=:loggedin",loggedin=session["user_id"])
                    if row and row[0]["cash"]-total>=0:
                    #Adding to the portfolio
                        row=db.execute("SELECT shares FROM stocks where stocksym=:sym and id=:id",sym=stocklist["symbol"],id=session["user_id"])
                    
                        db.execute("insert into history(id,stocksym,shares,price) values(:one,:two,:three,:four)",one=session["user_id"],two=stocklist["symbol"],three=int(request.form.get("shares")),four=stocklist["price"])
                
                    
                        if row:
                            db.execute("UPDATE stocks SET shares=shares+:value where id=:id AND stocksym=:name",value=int(request.form.get("shares")),id=session["user_id"],name=stocklist["symbol"])
                        else:
                            db.execute("INSERT into stocks(id,stocksym,shares,stockname,value) values(:id,:sym,:no_of,:stockname,:value)",\
                            id=session["user_id"],sym=stocklist["symbol"],\
                            no_of=int(request.form.get("shares")),\
                            stockname=stocklist["name"],\
                            value=stocklist["price"])
                        
                        db.execute("UPDATE users SET cash=cash-:value where id=:id ",value=total,id=session["user_id"])
                        rows=db.execute("select * from stocks where id=:id",id=session["user_id"])
                        return render_template("justbought.html",flag=0,boughtstocks=rows,message="Bought")
                
                    else:
                        return apology("Not enough cash to buy it!")
                else:
                    return apology("Not valid symbol")
            else:
                return apology("Not valid shares")
    return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    rows=db.execute("select * from history where id=:id order by transacted desc",id=session["user_id"])
    return render_template("history.html",boughtstocks=rows)
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))



@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
   
    if request.method=="POST":
        if bool(request.form.get("stockname",False))!=False:
            stocklist=lookup(request.form.get("stockname"))
            if stocklist:
                return render_template("showstock.html",name=stocklist["symbol"],actual_name=stocklist["name"],price=stocklist["price"])
            else: 
                return render_template("quote.html")
    return render_template("quote.html")
    
    
    
    
@app.route("/register", methods=["GET","POST"])
def register():
    # change this here
    if request.method=="GET":
        return render_template("register.html")
    elif request.method=="POST":
        if not bool(request.form.get("username",False))  or not bool(request.form.get("password",False)) or not request.form.get("password2",False):
            return apology("Must enter username and password")
        elif request.form.get("password")!=request.form.get("password2"):
            return apology("Entered passwords must match!!")
        else:
            row=db.execute("SELECT username from users where username=:user",user=request.form.get('username'))
            if not type(row) ==None and not len(row)==1:
                try:
                    encrypted=pwd_context.encrypt(request.form.get("password"))
                    db.execute("INSERT INTO users(username,hash) values(:user,:concealed)",user=request.form.get("username"),concealed=encrypted)
                except RuntimeError:
                    return render_template("register.html")
                
                session["user_id"] = row
                return redirect(url_for("index"))
            else:
                return apology("User already exists")

    #return apology("something is wrong")
        
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method=="POST":
        if request.form.get("stockname") and request.form.get("shares").isdigit() and int(request.form.get("shares"))>0:
            row=db.execute("SELECT * FROM stocks where id=:id and stocksym=:sym",id=session["user_id"],sym=request.form.get("stockname").upper())
            
            if row and row[0]["shares"]<int(request.form.get("shares")):
                return apology("Not enought shares")
            else:
                stocklist=lookup(request.form.get("stockname"))
                db.execute("Update users set cash=cash+:value",value=stocklist["price"]*int(request.form.get("shares")))
                
                db.execute("insert into history(id,stocksym,shares,price) values(:one,:two,:three,:four)",one=session["user_id"],two=stocklist["symbol"],three=int(request.form.get("shares"))*-1,four=stocklist["price"])
                
                if row[0]["shares"]==int(request.form.get("shares")):
                    db.execute("Delete from stocks where id=:id and stocksym=:sym",id=session["user_id"],sym=stocklist["symbol"])
                else:
                    db.execute("Update stocks set shares=shares-:gone where id=:id and stocksym=:sym",gone=int(request.form.get("shares")),id=session["user_id"],sym=stocklist["symbol"])
                    rows=db.execute("select * from stocks where id=:id",id=session["user_id"])
                    return render_template("justbought.html",flag=0,boughtstocks=rows,message="Sold")
        else:
            return apology("Stock name or shares are invalid")
    return render_template("sell.html")
    
@app.route("/passwordchange", methods=["GET", "POST"])
@login_required
def passwordchange():
    """Changing password."""
   
    if request.method=="POST":
        if request.form.get("oldpass") or request.form.get("password") or request.form.get("password2"):
           
            if request.form.get("password")==request.form.get("password2"):
                
                row=db.execute("select hash from users where id=:id",id=session["user_id"])
                
                if pwd_context.verify(request.form.get("oldpass"),row[0]["hash"]):
                    db.execute("Update users set hash =:newpass",newpass=pwd_context.encrypt(request.form.get("password")))
                    return apology("Password changed!")
                else:
                    return apology("Incorrect old password")
            else:
                return apology("Entered passwords don't match!")
        else:
            return apology("All fields should be filled!")
            
                
    return render_template("passwordchange.html")
    
