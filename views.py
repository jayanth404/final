from flask import Flask, request, Response, jsonify
from config import areas, dbaas, load_balancer, rides_dns_name
from datetime import datetime
import requests

app = Flask(__name__)


@app.errorhandler(405)
def four_zero_five(e):
	count()
	return Response(status=405)


@app.route('/api/v1/rides', methods=["POST"])
def function_to_create_ride():
	count()
	r_data = request.get_json(force=True)
	try:
		created_by = r_data['created_by']
		time_stamp = r_data['timestamp']
		source = int(r_data['source'])
		destination = int(r_data['destination'])
	except KeyError:
		return Response(status=400)

	try:
		req_date = convert_timestamp_to_datetime(time_stamp)
	except:
		return Response(status=400)

	if (source > len(areas) or destination > len(areas)) or (source < 1 or destination < 1):
		return Response(status=400)

	if not check_user_exist(created_by):
		print("User not present")
		return Response(status=400)

	try:
		file_read = requests.post('http://' + dbaas + '/api/v1/file/read', json={"file": "seq.txt"})
		ride_count = int(file_read.json()["latest_ride_id"])

		post_data = {
            "insert": [ride_count + 1, ride_count + 1, created_by, time_stamp, areas[source-1][1], areas[destination-1][1], []],
            "columns": ["_id", "rideId", "created_by", "timestamp", "source", "destination", "users"], "table": "rides"}
		response = requests.post('http://' + dbaas + '/api/v1/db/write', json=post_data)

		if response.status_code == 400:
			return Response(status=400)
		else:
			requests.post('http://' + dbaas + '/api/v1/file/write', json={"file": "seq.txt", "data": ride_count + 1})
			return Response(status=201, response='{}', mimetype='application/json')
	except:
		return Response(status=400)


@app.route('/api/v1/rides', methods=["GET"])
def function_to_list_rides_between_src_and_dst():
	count()
	source = request.args.get("source")
	destination = request.args.get("destination")

	if source is None or destination is None:
		return Response(status=400)

	try:
		source = int(source)
		destination = int(destination)
	except:
		return Response(status=400)

	if (source > len(areas) or destination > len(areas)) or (source < 1 or destination < 1):
		return Response(status=400)

	post_data = {"many": 1, "table": "rides", "columns": ["rideId", "created_by", "timestamp"],
                 "where": {"source": areas[source-1][1], "destination": areas[destination-1][1], "timestamp": {"$gt": convert_datetime_to_timestamp(datetime.now())}}}
	response = requests.post('http://' + dbaas + '/api/v1/db/read', json=post_data)

	if response.status_code == 400:
		return Response(status=400)

	result = response.json()
	for i in range(len(result)):
		if "_id" in result[i]:
			del result[i]["_id"]

	if not result:
		return Response(status=204)
	return jsonify(result)


@app.route('/api/v1/rides/<rideId>', methods=["GET"])
def function_to_get_details_of_ride(rideId):
	count()
	try:
		a = int(rideId)
	except:
		return Response(status=400)

	if request.method == "GET":
		post_data = {"table": "rides",
                     "columns": ["rideId", "created_by", "users", "timestamp", "source", "destination"],
                     "where": {"rideId": int(rideId)}}
		response = requests.post('http://' + dbaas + '/api/v1/db/read', json=post_data)
		if response.text == "":
			return Response(status=204, response='{}', mimetype='application/json')
		res = response.json()
		del res["_id"]
		return jsonify(res)
@app.route('/api/v1/rides/<rideId>', methods=["POST"])
def function_to_join_ride(rideId):
	count()
	try:
		a = int(rideId)
	except:
		return Response(status=400)
	if request.method == "POST":
		username = request.get_json(force=True)["username"]
		if not check_user_exist(username):
			return Response(status=400)

		post_data = {"table": "rides", "where": {"rideId": int(rideId)}, "update": "users", "data": username,
                     "operation": "addToSet"}
		response = requests.post('http://' + dbaas + '/api/v1/db/write', json=post_data)
		if response.status_code == 400:
			return Response(status=400)
		return jsonify({})
@app.route('/api/v1/rides/<rideId>', methods=["DELETE"])
def function_to_delete_ride(rideId):
	count()
	try:
		a = int(rideId)
	except:
		return Response(status=400)
	if request.method == "DELETE":
		post_data = {'column': 'rideId', 'delete': int(rideId), 'table': 'rides'}
		response = requests.post('http://' + dbaas + '/api/v1/db/write', json=post_data)
		if response.status_code == 400:
			return Response(status=400)
		return jsonify({})


@app.route('/api/v1/rides/count', methods=["GET"])
def function_to_get_no_of_rides():
	count()
	post_data = {"count": 1, "table": "rides"}
	response = requests.post('http://' + dbaas + '/api/v1/db/read', json=post_data)
	return jsonify(response.json())


@app.route('/api/v1/_count', methods=["GET"])
def requests_count():
	if request.method == "GET":
		f = open("requests_count.txt", "r")
		res = [int(f.read())]
		f.close()
		return jsonify(res)

@app.route('/api/v1/_count', methods=["DELETE"])
def requests_count():
	if request.method == "DELETE":
		f = open("requests_count.txt", "w")
		f.write("0")
		f.close()
		return jsonify({})


def check_user_exist(username):
	response = requests.get('http://' + load_balancer + '/api/v1/users', headers={"Origin": rides_dns_name})
	return response.status_code != 400 and username in response.json()


def convert_datetime_to_timestamp(k):
	day = str(k.day) if len(str(k.day)) == 2 else "0" + str(k.day)
	month = str(k.month) if len(str(k.month)) == 2 else "0" + str(k.month)
	year = str(k.year)
	second = str(k.second) if len(str(k.second)) == 2 else "0" + str(k.second)
	minute = str(k.minute) if len(str(k.minute)) == 2 else "0" + str(k.minute)
	hour = str(k.hour) if len(str(k.hour)) == 2 else "0" + str(k.hour)
	return day + "-" + month + "-" + year + ":" + second + "-" + minute + "-" + hour

def count():
	f = open("requests_count.txt", "r")
	count = int(f.read())
	f.close()
	f2 = open("requests_count.txt", "w")
	f2.write(str(count + 1))
	f2.close()

def convert_timestamp_to_datetime(time_stamp):
	day = int(time_stamp[0:2])
	month = int(time_stamp[3:5])
	year = int(time_stamp[6:10])
	seconds = int(time_stamp[11:13])
	minutes = int(time_stamp[14:16])
	hours = int(time_stamp[17:19])
	return datetime(year, month, day, hours, minutes, seconds)

if __name__ == "__main__":
	app.run(debug=True, host="0.0.0.0", port=80)
