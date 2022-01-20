package tests

import (
	"flamepaw/common"
	"io"
	"math/rand"
	"os"
	"strconv"
	"time"

	"github.com/sirupsen/logrus"
	log "github.com/sirupsen/logrus"
)

func Test() {
	rPage := func() string {
		rand.Seed(time.Now().UnixNano())
		pageRand := strconv.Itoa(rand.Intn(7))
		return pageRand
	}

	logFile, err := os.OpenFile("modules/infra/dragon/_logs/dragon-"+common.CreateUUID(), os.O_RDWR|os.O_CREATE, 0600)
	defer logFile.Close()
	if err != nil {
		panic(err.Error())
	}

	mw := io.MultiWriter(os.Stdout, logFile)
	logrus.SetOutput(mw)

	// Tests
	testURLStatus("GET", "/", 200)
	testURLStatus("GET", "/search/t?target_type=bot&q=Test", 200)
	testURLStatus("GET", "/search/t?target_type=server&q=Test", 200)
	testURLStatus("GET", "/search/t?target_type=invalid&q=Test", 422)
	testURLStatus("GET", "/mewbot", 200)
	testURLStatus("GET", "/furry", 200)
	testURLStatus("GET", "/_private", 404)
	testURLStatus("GET", "/fates/rules", 200)
	testURLStatus("GET", "/fates/thisshouldfail/maga2024", 404)
	testURLStatus("GET", "/bot/519850436899897346", 200)
	testURLStatus("GET", "/api/bots/0/random", 200)

	// Review html testing
	bots := []string{"519850436899897346", "101", "thisshouldfail", "1818181818188181818181818181"}
	var i int
	for i <= 10 {
		for _, bot := range bots {
			testURLStatus("GET", "/bot/"+bot+"/reviews_html?page="+rPage(), 200, 404, 400)
		}
		i += 1
	}
	log.Info("Result: " + strconv.Itoa(testsDone) + " tests done with " + strconv.Itoa(testsSuccess) + " successful")
}
