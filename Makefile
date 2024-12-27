.PHONY: all clean run-server run-client

all: fileclient fileserver

fileclient:
	cp fileclient.py fileclient
	chmod u+x fileclient

fileserver:
	cp fileserver.py fileserver
	chmod u+x fileserver

clean: fileclient fileserver
	rm fileclient fileserver

run-server: fileserver
	./fileserver -p 65432 -d ./root

run-client: fileclient
	./fileclient -h "" -p 65432