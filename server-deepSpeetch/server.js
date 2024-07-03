const DeepSpeech = require('deepspeech');
const Fs = require('fs');
const Sox = require('sox-stream');
const MemoryStream = require('memory-stream');
const Duplex = require('stream').Duplex;
const Wav = require('node-wav');
const http = require('http');

const PORT = 80;
const HTTP_ENDPOINT = 'http://127.0.0.1:5003';
const modelPath = '/home/aziz/deepspeech-0.9.3-models.pbmm';
const scorerPath = '/home/aziz/deepspeech-0.9.3-models.scorer';

let model;
try {
    model = new DeepSpeech.Model(modelPath);
    model.enableExternalScorer(scorerPath);
} catch (err) {
    console.error('Error loading model or scorer:', err);
    process.exit(1);
}

const desiredSampleRate = model.sampleRate();

const bufferToStream = (buffer) => {
    const stream = new Duplex();
    stream.push(buffer);
    stream.push(null);
    return stream;
};

const processAudioFile = (filePath, res) => {
    if (!Fs.existsSync(filePath)) {
        console.error('File not found:', filePath);
        res.writeHead(404, {'Content-Type': 'text/plain'});
        res.end('File not found');
        return;
    }

    const buffer = Fs.readFileSync(filePath);
    const result = Wav.decode(buffer);

    if (result.sampleRate < desiredSampleRate) {
        console.warn(`Warning: original sample rate (${result.sampleRate}) is lower than ${desiredSampleRate}Hz. Up-sampling might produce erratic speech recognition.`);
    }

    const audioStream = new MemoryStream();
    bufferToStream(buffer)
        .pipe(Sox({
            global: { 'no-dither': true },
            output: {
                bits: 16,
                rate: desiredSampleRate,
                channels: 1,
                encoding: 'signed-integer',
                endian: 'little',
                compression: 0.0,
                type: 'raw'
            }
        }))
        .pipe(audioStream);

    audioStream.on('finish', () => {
        const audioBuffer = audioStream.toBuffer();
        const audioLength = (audioBuffer.length / 2) * (1 / desiredSampleRate);
        console.log('Audio length:', audioLength);

        let result;
        try {
            result = model.stt(audioBuffer);
            console.log('STT result:', result);
        } catch (err) {
            console.error('Error during speech-to-text processing:', err);
            res.writeHead(500, {'Content-Type': 'text/plain'});
            res.end('Error during speech-to-text processing');
            return;
        }

        const data = JSON.stringify({ question: result });
        const url = new URL(HTTP_ENDPOINT);
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': data.length,
            },
        };

        const httpRequest = http.request(options, (httpResponse) => {
            let responseData = '';
            httpResponse.on('data', (chunk) => { responseData += chunk; });
            httpResponse.on('end', () => {
                if (httpResponse.statusCode === 200) {
                    console.log("Successfully sent the file path to the server Mixtral");
                } else {
                    console.error(`Failed to send the file path. HTTP status code: ${httpResponse.statusCode}`);
                }
                // End the response to close the client
                res.end();
            });
        });

        httpRequest.on('error', (e) => {
            console.error(`Error sending HTTP request: ${e.message}`);
            res.writeHead(500, {'Content-Type': 'text/plain'});
            res.end('Error sending HTTP request');
        });

        httpRequest.write(data);
        httpRequest.end();
    });
};

const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url === '/') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', () => {
            try {
                const json = JSON.parse(body);
                const filePath = json.file_path;

                if (filePath) {
                    console.log(`Received file path: ${filePath}`);
                    res.writeHead(200, {'Content-Type': 'text/plain'});
                    res.end('Successfully received the file path');
                    processAudioFile(filePath, res);
                } else {
                    res.writeHead(400, {'Content-Type': 'text/plain'});
                    res.end('No file path provided');
                }
            } catch (error) {
                res.writeHead(400, {'Content-Type': 'text/plain'});
                res.end('Invalid JSON');
            }
        });
    } else {
        res.writeHead(404, {'Content-Type': 'text/plain'});
        res.end('Not Found');
    }
});

server.listen(PORT, () => {
    console.log(`Server is listening on port ${PORT}`);
});
