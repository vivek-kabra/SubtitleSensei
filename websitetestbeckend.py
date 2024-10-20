from flask import Flask, render_template, request, send_file
import os
import whisper
import subprocess
import pysrt
import stable_whisper
import ffmpeg
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'


if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/')
def index():
    
    return render_template('website.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    
    mp4_file = request.files['mp4_file']
    srt_file = request.files['srt_file']

    if mp4_file and srt_file:
        
        mp4_path = os.path.join(app.config['UPLOAD_FOLDER'], mp4_file.filename)
        srt_path = os.path.join(app.config['UPLOAD_FOLDER'], srt_file.filename)
        mp4_file.save(mp4_path)
        srt_file.save(srt_path)

        
        with open(srt_path, 'r', encoding='utf-8') as f:
            original_srt = f.read()
        
        srt_file_path = os.path.join(app.config['UPLOAD_FOLDER'], srt_file.filename)
        video_file_path = os.path.join(app.config['UPLOAD_FOLDER'], mp4_file.filename)
        audio_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio.mp3')

        subprocess.run(['ffmpeg', '-i', video_file_path, '-q:a', '0', '-map', 'a', audio_file_path], check=True)
        def srt_to_transcript(srt_path):
            subs = pysrt.open(srt_path)
            
            transcript = ""
            for sub in subs:
                clean_text = sub.text.replace('<i>', '').replace('</i>', '')
                clean_text = clean_text.replace('\n', ' ')
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                if clean_text: 
                    transcript += clean_text + ' '

            return transcript

        model = stable_whisper.load_model("base")

        txt=srt_to_transcript(srt_file_path)

        result = model.align(audio_file_path, txt, language='en')

        segments = []
        for segment in result:
            for word in segment.words:
                text = word.word
                start_time = word.start
                end_time = word.end
                
                
                start_time_hms = "{:02d}:{:02d}:{:02d},{:03d}".format(
                    int(start_time // 3600),
                    int((start_time % 3600) // 60),
                    int(start_time % 60),
                    int((start_time % 1) * 1000)
                )
                
                end_time_hms = "{:02d}:{:02d}:{:02d},{:03d}".format(
                    int(end_time // 3600),
                    int((end_time % 3600) // 60),
                    int(end_time % 60),
                    int((end_time % 1) * 1000)
                )
                
                segments.append((''.join(c for c in text if c.isalnum()),start_time_hms,end_time_hms))

        subs = pysrt.open(srt_file_path)
        sub_list = list(subs)

        list_of_lines = []
        for sub in sub_list:
            text = sub.text
            text = text.split(" ")
            if text[0][0]=="<":
                text[0] = text[0][3:]
                text[-1] = text[-1][:-4]
            
            for i in range(len(text)):
                if "\n" in text[i]:
                    text[i:i+1] = text[i].split("\n")

                if "-" in text[i]:
                    text[i:i+1] = text[i].split("-")

            text = [x for x in text if x != '']
            list_of_lines.append(text)

        with open(srt_file_path, 'r') as file:
            lines = file.readlines()

        i=0
        k=0

        for j in range(len(lines)):
            if('-->' in lines[j]):
                b=len(list_of_lines[k])
                k+=1
                for l in range(b):
                    if segments[i][0]=="":
                        l-=1
                    else:
                        if (l==0):
                            new_start_time=segments[i][1]
                    i+=1
                i-=1
                new_end_time=segments[i][2]
                i+=1
                lines[j] = new_start_time + ' --> ' + new_end_time + '\n'



        with open("uploads/new_sub.srt", 'w') as file:
            file.writelines(lines)
        
        
        improved_srt_path = os.path.join(app.config['UPLOAD_FOLDER'], 'new_sub.srt')        
        os.remove(audio_file_path)
        os.remove(video_file_path)
        
        
        return send_file(improved_srt_path, as_attachment=True)
    
       
        

    return 'No file uploaded', 400


if __name__ == '__main__':
    app.run(debug=True)
