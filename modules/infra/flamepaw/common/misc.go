package common

import (
	"os"
	"runtime/debug"

	"github.com/davecgh/go-spew/spew"
	log "github.com/sirupsen/logrus"
)

var CatName = RandString(64)

func PanicDump() {
	err := recover()
	if err != nil {
		trace := spew.Sdump(err) + "\n" + string(debug.Stack())
		os.WriteFile("modules/infra/flamepaw/panic-"+CatName+".txt", []byte(trace), 0644)
		log.Error(string(trace))
		os.Exit(-1)
	}
}
