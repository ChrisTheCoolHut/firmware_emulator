echo '
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Server: netcat!

<!doctype html>
<img class="transparent" src="https://cataas.com/cat/gif"></img>
<html><body><h1>Unauthenticated Cat gifs!</h1></body></html>
' | nc -lp 12345
