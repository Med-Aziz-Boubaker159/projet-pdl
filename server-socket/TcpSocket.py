import socket
import wave
import struct
import time
import requests

# Server details
SERVER_IP = "0.0.0.0"  # Listen on all available interfaces
SERVER_PORT = 8888
CONNECTION_TIMEOUT = 15  # Timeout in seconds
HTTP_ENDPOINT = "http://127.0.0.1:80"  # Replace with your HTTP endpoint

# Create a TCP/IP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
server_socket.bind((SERVER_IP, SERVER_PORT))
server_socket.listen(1)
print(f"Server listening on {SERVER_IP}:{SERVER_PORT}")

try:
    #while True:
        print("Waiting for a connection...")
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        start_time = time.time()  # Record the start time

        try:
            with open("adc.raw", "ab") as f:  # Open the file in binary append mode
                while True:
                    if time.time() - start_time > CONNECTION_TIMEOUT:
                        print("Connection timed out")
                        break

                    data = client_socket.recv(1024)  # Receive data in 1024-byte chunks
                    if not data:
                        break
                    f.write(data)  # Write the received data to the file

        except Exception as e:
            print(f"Error during data reception: {e}")

        finally:
            print("Closing connection")
            client_socket.close()

except KeyboardInterrupt:
    print("Server shutting down")

finally:
    server_socket.close()

# Configuration parameters
input_file = 'adc.raw'      # Your raw I2S file
output_file = 'output.wav'  # Desired output WAV file
sample_rate = 48000         # Sample rate in Hz
num_channels = 1            # Number of audio channels (1 for mono, 2 for stereo)
sample_width = 2            # Sample width in bytes (2 bytes for 16-bit samples)
endianness = 'little'       # 'little' for little-endian, 'big' for big-endian

try:
    # Open the raw I2S file
    with open(input_file, 'rb') as raw_file:
        raw_data = raw_file.read()

    print(f"Read {len(raw_data)} bytes from {input_file}")

    # Create a new WAV file
    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        # Process and write raw I2S data to the WAV file
        if endianness == 'little':
            format_char = '<h'  # Little-endian 16-bit
        else:
            format_char = '>h'  # Big-endian 16-bit

        # Convert raw data to the appropriate format and write it
        for i in range(0, len(raw_data), sample_width):
            sample = struct.unpack(format_char, raw_data[i:i+sample_width])[0]
            wav_file.writeframesraw(struct.pack('<h', sample))  # Convert to little-endian for WAV

    print(f'Conversion complete. Output file: {output_file}')

    # Send the path of the output file to the HTTP endpoint
    try:
        path_file = "/home/aziz/esp32_audio-master/server/javascript/output.wav"
        response = requests.post(HTTP_ENDPOINT, json={'file_path': path_file})
        if response.status_code == 200:
            print("Successfully sent the file path to the server DeepSpeesh")
        else:
            print(f"Failed to send the file path. HTTP status code: {response.status_code}")

    except Exception as e:
        print(f"Error sending HTTP request: {e}")

except Exception as e:
    print(f"Error during file conversion: {e}")
