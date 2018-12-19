from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from pymongo import MongoClient
import bcrypt
import numpy
import requests
import subprocess
import json

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.ImageClassiferDB
users = db["Users"]

def userExist(username):
    if users.find({ "Username" : username }).count() == 0:
        return False
    else:
        return True

def verify_pw(username, password):
    if not userExist(username):
        return False

    hashed_pw = users.find({ "Username" : username })[0]["Password"]
    if bcrypt.hashpw(password.encode("utf8"), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def verifyCredentional(username, password ):
    if not userExist(username):
        return genrateReturnJson(301, "Invalid username") , True
    
    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return genrateReturnJson(302, "Invalid password") , True

    return None , False

def genrateReturnJson(status,  message):
    return {
        "status" : status,
        "message" : message
    }

def countTokens(usename):
    return users.find({
        "Username" : usename
    })[0]["Tokens"]


class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        if userExist(username):
            return jsonify( genrateReturnJson( 301 , "Invalid user"))

        hashed_pw = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

        users.insert({
            "Username" : username,
            "Password" : hashed_pw,
            "Tokens"    : 6
        })

        return jsonify( genrateReturnJson(200, "User signed up successfully to API!"))

class Classify(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        url = postedData["url"]

        retJson, error = verifyCredentional(username, password)
        if error:
            return jsonify(retJson)

        num_tokens = countTokens(username)

        if num_tokens <= 0:
            return jsonify( genrateReturnJson(303, "Out of tokens. Please refill your tokens" ))

        r = requests.get(url)
       
        retJson = {}
        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            proc = subprocess.Popen(['python','classify_image.py','--model_dir=.','--image_file=./temp.jpg'])
            proc.communicate()[0]
            proc.wait()
            with open('text.txt') as g:
                retJson = json.load(g)
                
        # correct_admin_pw = "abc123"

        # if not admin_pw == correct_admin_pw:
        #     return jsonify( genrateReturnJson( 304, "Invalid Adminstrator Password"))
            
        users.update({
            "Username" : username
        }, {
            "$set" : {
                "Tokens" : num_tokens - 1
            }
        })
        return retJson

class Refill(Resource):
    def post(self): 
        
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        refill = postedData["refill"]

        retJson, error = verifyCredentional(username, password)
        if error:
            return jsonify(retJson)
        
        num_tokens = countTokens(username)
        print('tokens' + str(num_tokens))

        users.update({
            "Username" : username
        }, {
            "$set":
            {
                "Tokens" : int(num_tokens + refill)
            }
        })

        newCount = countTokens(username)
        retJson = {
            "status" : 200,
            "message": "Your tokens are updated successfully!",
            "count" : newCount

        }
        return jsonify(retJson)

api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)