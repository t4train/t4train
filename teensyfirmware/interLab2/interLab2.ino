#define CAPTURE_SIZE 1500

uint16_t input[CAPTURE_SIZE+2];

double f_start = 100e3;
double f_end = 1e6;

int sig = 11;
int sync = 12;

uint8_t delimiter[] = {0xde, 0xad, 0xbe, 0xef};
int delimeter_length = 4;

void setup() {
  pinMode(sig, OUTPUT);
  pinMode(sync, OUTPUT);
  Serial.begin(2000000);

  // Set the Teensy ADC to 12-bit resolution
  analogReadResolution(12);
  
  //analogWriteResolution(7);
  analogWriteFrequency(sig,1e4);
  analogWrite(sig, 127);
}

void loop ()
{
  collect_sample();
  send_sample();
}

void collect_sample() {
  // Reset the index for the input buffer
  int i = 0;

  // Set sync signal
  digitalWrite(sync, HIGH);

  // Loop through CAPTURE_SIZE samples and frequency sweep steps
  while(i < CAPTURE_SIZE) {
    input[i] = analogRead(0);
//    Serial.println(input[i]);
    i++;

    int f = pow(10, (log10(f_end-f_start)*((i*1.0)/(CAPTURE_SIZE-1)))) + f_start; // logarithmic
    
    analogWriteFrequency(sig, f);
    analogWrite(sig, 127);
    
    //delayMicroseconds(1000);
  }

  // Reset sync signal
  digitalWrite(sync, LOW);
}

void send_sample() {
  // Print the delimiter
  /*for(int k = 0; k < delimeter_length; k++) {
    Serial.write(delimiter[k]);
  }*/
  Serial.write(delimiter, sizeof(delimiter));

  // Channel byte (one at the end of each channel's transmission)
  input[CAPTURE_SIZE] = 0;
  // Frame completion byte (only after all channels sent)
  input[CAPTURE_SIZE+1] = 1;

  // Print the data
  /*for(int k = 0; k < CAPTURE_SIZE; k++) {
    Serial.write((uint8_t)(input[k]>>8));
    Serial.write((uint8_t)(input[k]));
  }*/
  Serial.write((uint8_t *)input, sizeof(input));
}
