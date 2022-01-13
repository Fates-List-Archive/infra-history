all:
	#go build -v -ldflags="${LDFLAGS}" -o dragon-dyn
	CGO_ENABLED=0 GOAMD64=v3 go build -v
install:
	cp dragon /usr/local/bin
