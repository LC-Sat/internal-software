from flask import Flask, render_template, redirect, send_from_directory, request, abort, jsonify, Response, send_file
import os
import logging

app = Flask(__name__)

sat = None
DATA_PATH = None


@app.route('/')
def index():
    mode = ["AUTO", "MANUAL", "DELAY"][sat.mode]
    nb = sat.data_nb - 1
    return render_template("index.html", mode=mode, sat=sat, nb=nb)


@app.route("/api/capture/start")
def start_capture():
    print("Start capture (webapp)")
    sat.start_capture()
    return Response(status=204)


@app.route("/api/capture/stop")
def stop_capture():
    print("Stop capture (webapp)")
    sat.stop_capture()
    return Response(status=202)


@app.route("/api/download")
def download():
    nb = request.args.get("data_nb")
    if nb is None:
        nb = sat.data_nb - 1
    if not os.path.exists(DATA_PATH+"/data{}.tar.gz".format(nb)):
        return abort(404)
    return send_from_directory(DATA_PATH, "data{}.tar.gz".format(nb))


@app.route("/api/buzzer/start")
def start_buzz():
    sat.start_buzzer()
    return Response(status=204)


@app.route("/api/buzzer/stop")
def stop_buzz():
    sat.stop_buzzer()
    return Response(status=204)


@app.route("/api/cansat/shutdown")
def shutdown():
    sat.shutdown()
    return redirect("/shutdown")


@app.route("/shutdown")
def shutdown_status():
    shut = sat.shutdown_flag
    run = sat.running
    sav = sat.saving
    if shut or run or sav:
        status = "Arrêt en cours"
    else:
        status = "Arrêté"
    return render_template("shutdown.html", status=status)


@app.route("/api/cansat/status")
def cansat_status():
    return jsonify({
        "running": sat.running,
        "capturing": sat.capture,
        "saving": sat.saving,
        "wifi": sat.wifi,
        "encryption": sat.encryption,
        "buzzer": sat.buzzer_on,
        "mode": ["AUTO", "MANUAL", "DELAY"][sat.mode],
        "last_data": sat.data_nb - 1,
        "sensors": {
            "camera": sat.cam_enabled,
            "bmp": sat.bmp_enabled,
            "accel": sat.accel_enabled,
            "gps": sat.gps_enabled,
            "th_cam": sat.th_cam_enabled,
            "humidity": sat.hum_enabled
        }
    })


@app.route("/api/cansat/status/shutdown")
def shutdown_status_api():
    shut = sat.shutdown_flag
    run = sat.running
    sav = sat.saving
    return jsonify({
        "shutdown": shut,
        "done": not (run or sav)
    })


@app.route("/api/encryption/enable")
def enable_encryption():
    sat.encryption = True
    return Response(status=204)


@app.route("/api/encryption/disable")
def disable_encryption():
    sat.encryption = False
    return Response(status=204)


@app.route("/api/cansat/logs")
def get_logs():
    if not os.path.exists("log.txt"):
        return abort(404)
    return send_file("log.txt")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
