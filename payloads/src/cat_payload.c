/* --- server.c --- */
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>
#include <time.h>

char cat_html[] = 
	"HTTP/1.1 200 OK\n"
	"Content-Type: text/html; charset=UTF-8\n"
	"Server: cat_server\n\n"
	"<!doctype html>\n"
	"<img class=\"transparent\" src=\"https://cataas.com/cat/gif\"></img>\n"
	"<html><body><h1>Unauthenticated Cat gifs!</h1></body></html>\n\n";

int main(int argc, char *argv[])
{
	int listenfd = 0, connfd = 0;
	struct sockaddr_in serv_addr;

	if(argc != 2)
	{
		fprintf(stderr, "Usage: %s <Port number>\n", argv[0]);
		exit(-1);
	}

	fprintf(stderr, "Running on port %s\n", argv[1]);

	int port = atoi(argv[1]);

	/* creates an UN-named socket inside the kernel and returns
	 * an integer known as socket descriptor
	 * This function takes domain/family as its first argument.
	 * For Internet family of IPv4 addresses we use AF_INET
	 */
	listenfd = socket(AF_INET, SOCK_STREAM, 0);
	memset(&serv_addr, '0', sizeof(serv_addr));

	serv_addr.sin_family = AF_INET;
	serv_addr.sin_addr.s_addr = htonl(INADDR_ANY);
	serv_addr.sin_port = htons(port);

	/* The call to the function "bind()" assigns the details specified
	 * in the structure 『serv_addr' to the socket created in the step above
	 */
	bind(listenfd, (struct sockaddr*)&serv_addr, sizeof(serv_addr));

	/* The call to the function "listen()" with second argument as 10 specifies
	 * maximum number of client connections that server will queue for this
	 * listening
	 * socket.
	 */
	listen(listenfd, 10);

	while(1)
	{
		/* In the call to accept(), the server is put to sleep and when
		 * for an incoming
		 * client request, the three way TCP handshake* is complete, the
		 * function accept()
		 * wakes up and returns the socket descriptor representing the
		 * client socket.
		 */
		connfd = accept(listenfd, (struct sockaddr*)NULL, NULL);

		fprintf(stderr, "New connection!\n");
		write(connfd, cat_html, strlen(cat_html));

		sleep(1);
		//close(connfd);
	}
}
