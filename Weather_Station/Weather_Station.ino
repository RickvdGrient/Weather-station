#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

#include <Bonezegei_DHT11.h>

int TEMPSENSOR = 2;

const char* ssid = "Ziggo3969131";
const char* password = "mkmyywh4hkV7darN";

//Your Domain name with URL path or IP address with path
String serverName = "http://192.168.178.52:5000/update-sensor";

unsigned long lastTime = 0;
unsigned long timerDelay = 3000;// 600000;

Bonezegei_DHT11 DhtSensor( TEMPSENSOR );

void setup() {
  Serial.begin( 9600 );

  WiFi.begin( ssid, password );
  Serial.println( "Connecting" );

  while ( WiFi.status() != WL_CONNECTED )
  {
    delay( 500 );
    Serial.print( "." );
  }

  Serial.println( "" );
  Serial.print( "Connected to WiFi network with IP Address: " );
  Serial.println( WiFi.localIP() );

  DhtSensor.begin();
  randomSeed(analogRead(0));
}

void loop() {
  DhtSensor.getData();

  if ( ( millis() - lastTime ) > timerDelay )
  {
    //Check WiFi connection status
    if ( WiFi.status() == WL_CONNECTED )
    {
      WiFiClient client;
      HTTPClient http;

      String serverPath = serverName + "?temperature=" + String( float( DhtSensor.getTemperature() ) );
      Serial.println( float( DhtSensor.getTemperature() ) );

      http.begin( client, serverPath.c_str() );

      int httpResponseCode = http.GET();

      if ( httpResponseCode != 200 )
      {
        Serial.print( "Error code: " );
        Serial.println( httpResponseCode );
      }

      http.end();
    }
    else
    {
      Serial.println( "WiFi Disconnected" );
    }
    lastTime = millis();
  }

}
