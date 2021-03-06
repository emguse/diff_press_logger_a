import diff_p_DLHR_F50D as DLHR_F50D
from polling_timer import PollingTimer
from move_ave import MovingAverage
from collections import deque
from wave_save import WavSave
from buzz_pipi_r import PiPi
from print_with_DP_EH600 import PrintWithDpEh600
import datetime
import multiprocessing as mp

SAMPLE_FREQ = 32 # Hz
SAMPLE_INTERVAL = 1/SAMPLE_FREQ # 
IVENT_LENGTH = 30 # sec
QUE_SIZE = int(IVENT_LENGTH/2 * SAMPLE_FREQ)
MOVE_AVE_LENGTH = 4
REFARENCE_PAST_SAMPLE = 4
THRESHOLD = 0.4
MAX_VALUE = 125
SAVE_DIR = './log/'

ZERO_OFFSET = 1.9 # Zero point correction
USE_PRINTER = True
USE_CSV_EXPORT = True
USE_WAV_EXPORT = False

def thermal_printing(data) -> None:
    if USE_PRINTER == True:
        for s in data:
            p = PrintWithDpEh600()
            p.printing(s)
        p.line_feed(1)

def sound_buzzer():
    pipi = PiPi()
    pipi.pipi()

def export_csv(d_a):
    now = datetime.datetime.now()
    now_iso = now.strftime('%Y-%m-%d') + 'T' + now.strftime('%H_%M_%S_%f')
    filename = str(SAVE_DIR + now_iso + '.csv')
    try:
        with open(filename, 'w', newline='') as f:
            #writer = csv.writer(f)
            print("Start exporting data")
            for i in d_a:
                #writer.writerow(i)
                f.write(str(i)+'\n')
            print("Export Complete")
    except:
        print("File export error")

def main():
    dlhr_f50d = DLHR_F50D.DLHR_F50D()
    read_intarval = PollingTimer(SAMPLE_INTERVAL)
    record_intarval = PollingTimer(IVENT_LENGTH/2)
    record_intarval.up_state = True
    ma = MovingAverage(MOVE_AVE_LENGTH)
    dq_p = deque(maxlen=QUE_SIZE)
    dq_ref = deque(maxlen=REFARENCE_PAST_SAMPLE)
    dq_after = deque(maxlen=QUE_SIZE)

    wavesave = WavSave()
    wavesave.set_wav_param(1,2,SAMPLE_FREQ)
    wavesave.set_norm(MAX_VALUE)

    for _ in range(MOVE_AVE_LENGTH):
        while True:
            read_intarval.timer_update()
            if read_intarval.up_state == True:
                dlhr_f50d.read_p()
                ma_p = ma.simple_moving_average(dlhr_f50d.pressure - ZERO_OFFSET)
                dq_p.append(ma_p)
                dq_ref.append(ma_p)
                break

    while True:
        read_intarval.timer_update()
        if read_intarval.up_state == True:
            dlhr_f50d.read_p()
            ma_p = ma.simple_moving_average(dlhr_f50d.pressure - ZERO_OFFSET)
            dq_p.append(ma_p)
            dq_ref.append(ma_p)
            if abs(dq_ref[0])+THRESHOLD <= abs(ma_p):
                record_intarval.timer_update_only()
                if record_intarval.up_state == True:
                    record_intarval.up_state = False

                    buzzer_process = mp.Process(target=sound_buzzer)
                    buzzer_process.start()
                    
                    data = []
                    now = datetime.datetime.now()
                    data.append(now.strftime('%Y-%m-%d') + 'T' + now.strftime('%H:%M:%S.%f'))
                    data.append('DP:' + str(round(ma_p, 4)) + '  ??P:' + str(round((dq_ref[0] - ma_p),4)))
                    print_process = mp.Process(target=thermal_printing, args=(data,))
                    print_process.start()

                    for i in range(QUE_SIZE):
                        while True:
                            read_intarval.timer_update()
                            if read_intarval.up_state == True:
                                dlhr_f50d.read_p()
                                ma_p = ma.simple_moving_average(dlhr_f50d.pressure - ZERO_OFFSET)
                                dq_after.append(ma_p)
                                dq_ref.append(ma_p)
                                break
                    ar = list(dq_p)
                    ar.extend(dq_after)
                    if USE_WAV_EXPORT == True:
                        wavesave.save_w_date(dq_p)
                    if USE_CSV_EXPORT == True:
                        export_csv(ar)

if __name__ == '__main__':
    main()