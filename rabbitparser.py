
#!/usr/bin/env python
import pika


credentials = pika.PlainCredentials('hackaton', 'QtGcmpPm')
connection = pika.BlockingConnection(
    pika.ConnectionParameters('185.143.172.238',
                                       5672,
                                       '/',
                                       credentials))
channel = connection.channel()

channel.queue_declare(queue='hello')
f = open('history.txt', 'a+')

def callback(ch, method, properties, body):
    f.write(body)
    print(body)


channel.basic_consume(
    queue='telemetry', on_message_callback=callback, auto_ack=True)

channel.start_consuming()
f.close()
