package main

import (
	"dragon/common"
	"dragon/server"
	"io"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
	log "github.com/sirupsen/logrus"
)

func main() {
	lvl, ok := os.LookupEnv("LOG_LEVEL")
	if !ok {
		lvl = "debug"
	}
	ll, err := log.ParseLevel(lvl)
	if err != nil {
		ll = log.DebugLevel
	}
	log.SetLevel(ll)

	if common.CliCmd == "dragon.server" {
		server.DragonServer()
		os.Exit(0)
	} else if common.CliCmd == "dragon.test" {
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
	} else {
		cmdFunc := strings.Replace(common.CliCmd, ".", "_", -1)
		pyCmd := "from modules.core._manage import " + cmdFunc + "; " + cmdFunc + "()"
		log.Info("Running " + common.PythonPath + " -c '" + pyCmd + "'")
		os.Setenv("MAIN_TOKEN", common.MainBotToken)
		os.Setenv("CLIENT_SECRET", common.ClientSecret)
		os.Setenv("PYTHONPYCACHEPREFIX", common.RootPath+"/data/pycache")
		if os.Getenv("PYLOG_LEVEL") != "debug" {
			os.Setenv("LOGURU_LEVEL", "INFO")
		}
		devserver := exec.Command(common.PythonPath, "-c", pyCmd)
		devserver.Dir = common.RootPath
		devserver.Env = os.Environ()
		devserver.Stdout = os.Stdout
		devserver.Stderr = os.Stderr
		devserver.Run()
	}
}

func testURLStatus(method string, url string, statusCode ...int) bool {
	log.Info("Testing " + url + " with method " + method)
	testsDone += 1
	url = siteUrl + url
	client := http.Client{Timeout: 15 * time.Second}
	var resp *http.Response
	var err error

	if method == "GET" {
		resp, err = client.Get(url)
	} else if method == "HEAD" {
		resp, err = client.Head(url)
	} else {
		log.Error("FAIL: Invalid method " + method + " in test for URL " + url)
		return false
	}

	if err != nil {
		log.Error("FAIL: " + err.Error())
		return false
	}

	if resp.Request.URL.String() == siteUrl+"/maint/page" {
		log.Error("FAIL: Got maintainance page")
		return false
	}

	var checkPassed = false
	var codes = ""
	var no5xx = false
	for i, code := range statusCode {
		if resp.StatusCode == code || code == 0 {
			checkPassed = true
		} else if code == 0 {
			no5xx = true
		}
		if i == 0 {
			codes += strconv.Itoa(code)
		} else {
			codes = codes + "/" + strconv.Itoa(code)
		}
	}

	if !checkPassed {
		log.Error("FAIL: Expected status code " + codes + " but got status code " + strconv.Itoa(resp.StatusCode))
		return false
	}

	if no5xx && resp.StatusCode >= 500 {
		log.Error("FAIL: Got 5xx error: " + strconv.Itoa(resp.StatusCode))
		return false
	}

	log.Info("PASS: With status code " + strconv.Itoa(resp.StatusCode))
	testsSuccess += 1
	return true
}
