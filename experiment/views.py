from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth import login as LOGIN
from pi_server.tables.models import Slot, Account, Experiment, Booking
import json, datetime, os, time
from django.views.decorators.csrf import csrf_exempt
from pi_server import settings
# Create your views here.
# 
def check_connection(req):
    return HttpResponse("TESTOK")

@csrf_exempt
def initiation(req):
    username = req.POST.get("username")
    password = req.POST.get("password")
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            user1 = Account.objects.select_related().filter(id=user.id)
            user1 = user1[0]
            user_board = user1.board

	    #allows admin to access the temporary offline devices but prohibits the users to do so
            if user_board.online and (not user_board.temp_offline or user1.is_admin): 
                slots = Slot.slots_now()
                slot_ids = [s.id for s in slots]
                now = datetime.datetime.now()
                bookings = user.booking_set.filter(booking_date__year=now.year,
                                                booking_date__month=now.month,
                                                booking_date__day=now.day,
                                                slot_id__in=slot_ids).select_related("slot")
                try:
                    cur_booking = bookings[0]
                    active_slot = cur_booking.slot
                except:
                    cur_booking = None
                    active_slot = None

                if active_slot is not None:
                    endtime = cur_booking.end_time()
                    if now < endtime:
                        filename = datetime.datetime.strftime(now, "%Y%b%d_%H_%M_%S.txt")
                        logdir = os.path.join(settings.EXPERIMENT_LOGS_DIR, user.username)
                        if not os.path.exists(logdir):
                            os.makedirs(logdir)

                        f = open(os.path.join(logdir, filename), "a")
                        f.close()

                        LOGIN(req, user)

                        e = Experiment()
                        e.booking=cur_booking
                        e.log=user.username + "/" + filename
                        e.save()

                        key = str(user_board.mid)
			
                        settings.boards[key]["experiment_id"] = e.id
                            
                        reset(req)

                        STATUS = 1
                        MESSAGE = filename
                    else:
                        reset(req)
                        STATUS = 0
                        MESSAGE = "Slot has ended. Please book the next slot to continue the experiment."
                else:
                    STATUS = 0
                    MESSAGE = "You haven't booked this slot."
            else:
                STATUS = 0
                MESSAGE = "Your SBHS is offline. Please contact the Vlabs team."
        else:
            STATUS = 0
            MESSAGE = "Your account is not activated yet. Please check your email for activation link."
    else:
        STATUS = 0
        MESSAGE = "Invalid username or password"

    return HttpResponse(json.dumps({"STATUS": STATUS, "MESSAGE": MESSAGE}))

@login_required(redirect_field_name=None)
@csrf_exempt
def experiment(req):
    try:
        server_start_ts = int(time.time() * 1000)
        from pi_server.settings import boards
        user = req.user
        key = str(user.board.mid)
        experiment = Experiment.objects.select_related().filter(id=boards[key]["experiment_id"])

        if len(experiment) == 1 and user.id == experiment[0].booking.account.id and experiment[0].booking.trashed_at == None:
            experiment = experiment[0]
            now = datetime.datetime.now()
            endtime = experiment.booking.end_time()
            if endtime > now:
                timeleft = int((endtime-now).seconds)
                heat = max(min(int(req.POST.get("heat")), 100), 0)
                fan = max(min(int(req.POST.get("fan")), 100), 0)

                boards[key]["board"].setHeat(heat)
                boards[key]["board"].setFan(fan)
                temperature = boards[key]["board"].getTemp()
                log_data(boards[key]["board"], key, experiment.id, heat=heat, fan=fan, temp=temperature)

                server_end_ts = int(time.time() * 1000)

                STATUS = 1
                MESSAGE = "%s %d %d %2.2f" % (req.POST.get("iteration"),
                                            heat,
                                            fan,
                                            temperature)
                MESSAGE = "%s %s %d %d,%s,%d" % (MESSAGE,
                                            req.POST.get("timestamp"),
                                            server_start_ts,
                                            server_end_ts,
                                            req.POST.get("variables"), timeleft)

                f = open(os.path.join(settings.EXPERIMENT_LOGS_DIR, experiment.log), "a")
                f.write(" ".join(MESSAGE.split(",")[:2]) + "\n")
                f.close()
            else:
                # boards[key]["board"].setHeat(0)
                # boards[key]["board"].setFan(100)
                # log_data(boards[key]["board"], key)
                reset(req)
                
                STATUS = 0
                MESSAGE = "Slot has ended. Please book the next slot to continue the experiment."

                reset(req)
                boards[key]["experiment_id"] = None
        else:
            STATUS = 0
            MESSAGE = "You haven't booked this slot."

        return HttpResponse(json.dumps({"STATUS": STATUS, "MESSAGE": MESSAGE}))
    except Exception:
        return HttpResponse(json.dumps({"STATUS": 0, "MESSAGE": "Invalid input. Perhaps the slot has ended. Please book the next slot to continue the experiment."}))

@csrf_exempt
def reset(req):
    try:
        from pi_server.settings import boards
        user = req.user
        if user.is_authenticated():
            key = str(user.board.mid)
            experiment = Experiment.objects.select_related().filter(id=boards[key]["experiment_id"])

            if len(experiment) == 1 and user == experiment[0].booking.account:
                experiment = experiment[0]
                now = datetime.datetime.now()
                endtime = experiment.booking.end_time()

                boards[key]["board"].setHeat(0)
                boards[key]["board"].setFan(100)

                log_data(boards[key]["board"], key, experiment.id, 0, 100)
                if endtime < now:
                    boards[key]["experiment_id"] = None
    except:
        pass

    return HttpResponse("")

def client_version(req):
    return HttpResponse("3")

def log_data(sbhs, mid, experiment_id, heat=None, fan=None, temp=None):
    if heat is None:
        heat = sbhs.getHeat()
    if fan is None:
        fan = sbhs.getFan()
    if temp is None:
        temp = sbhs.getTemp()

    data = "%d %s %s %s\n" % (int(time.time()), str(heat), str(fan), str(temp))
    global_logfile = settings.SBHS_GLOBAL_LOG_DIR + "/" + str(mid) + ".log"
    with open(global_logfile, "a") as global_loghandler:
        global_loghandler.write(data)

def validate_log_file(req):
    import hashlib
    data = req.POST.get("data")
    data = data.strip().split("\n")
    clean_data = ""
    for line in data:
        columns = line.split(" ")
        if len(columns) >= 6:
            clean_data += (" ".join(columns[0:6]) + "\n")

    checksum = hashlib.sha1(clean_data).hexdigest()

    try:
        e = Experiment.objects.get(checksum=checksum)
        return HttpResponse("TRUE")
    except:
        return HttpResponse("FALSE")
