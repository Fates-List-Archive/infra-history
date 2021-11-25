package main

import (
	"app/types"
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	_ "net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"gioui.org/app"
	_ "gioui.org/app/permission/networkstate"
	"gioui.org/font/gofont"
	"gioui.org/io/pointer"
	"gioui.org/io/system"
	"gioui.org/layout"
	"gioui.org/op"
	"gioui.org/widget/material"
)

var reqCache map[string][]byte = make(map[string][]byte)

func requestRecover() {
	if r := recover(); r != nil {
		fmt.Println(r)
	}
}

func request(client http.Client, method string, path string, headers map[string]string, body map[string]interface{}) (respbody []byte, err error) {
	defer requestRecover()
	if method == "GET" {
		if v, ok := reqCache[method+":"+path]; ok {
			return v, nil
		}
	}

	if strings.HasPrefix(path, "/") {
		path = "https://fateslist.xyz" + path
	}

	url, err := url.Parse(path)
	if err != nil {
		return []byte{}, err
	}

	req := http.Request{
		Method: method,
		URL:    url,
	}

	if method != "GET" && body != nil {
		jsonStr, err := json.Marshal(body)
		if err != nil {
			return []byte{}, err
		}
		req.Body = ioutil.NopCloser(bytes.NewBuffer(jsonStr))
	}

	resp, err := client.Do(&req)

	if err != nil {
		return []byte{}, err
	}

	respbody, err = ioutil.ReadAll(resp.Body)
	if err != nil {
		return []byte{}, err
	}

	if method == "GET" {
		reqCache[method+":"+path] = respbody
	}

	return respbody, nil
}

func main() {
	go func() {
		// create new window
		w := app.NewWindow(
			app.Title("Fates List Go Experiment"),
		)

		// ops are the operations from the UI
		var ops op.Ops

		pointer.InputOp{
			Tag:   func() {},
			Types: pointer.Press | pointer.Drag | pointer.Release | pointer.Scroll,
		}.Add(&ops)

		var client = http.Client{Timeout: 15 * time.Second}

		var botData, err = request(client, "GET", "/api/index?type=0", map[string]string{}, map[string]interface{}{})

		if err != nil {
			fmt.Println(err.Error())
		}

		var botDataJson types.Index
		err = json.Unmarshal(botData, &botDataJson)

		if err != nil {
			fmt.Println(err.Error())
			return
		}

		fmt.Println(string(botData))

		// th defnes the material design style
		th := material.NewTheme(gofont.Collection())

		var list = layout.List{Axis: layout.Vertical}

		// listen for events in the window.
		for e := range w.Events() {
			// detect what type of event
			switch e := e.(type) {

			// this is sent when the application should re-render.
			case system.FrameEvent:
				gtx := layout.NewContext(&ops, e)

				list.Layout(gtx, 1, func(gtx layout.Context, i int) layout.Dimensions {
					return renderIndexPage("bots", gtx, botDataJson, th)
				})
				e.Frame(gtx.Ops)
			}
		}
	}()
	app.Main()
}
