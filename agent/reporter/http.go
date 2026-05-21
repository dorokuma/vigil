package reporter

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
	"vigil-agent/collector"
)

type Reporter struct {
	serverURL string
	hostname  string
	client    *http.Client
}

func New(serverURL, hostname string) *Reporter {
	return &Reporter{
		serverURL: serverURL,
		hostname:  hostname,
		client:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (r *Reporter) Report(data collector.ReportData) error {
	payload := map[string]interface{}{
		"hostname": r.hostname,
		"data":     data,
		"type":     "heartbeat",
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("JSON marshal failed: %w", err)
	}
	resp, err := r.client.Post(r.serverURL+"/report", "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("HTTP request failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("server returned %d", resp.StatusCode)
	}
	log.Printf("Report OK - %s (%s)", r.hostname, r.serverURL)
	return nil
}

func (r *Reporter) ReportOffline() error {
	payload := map[string]interface{}{
		"hostname":  r.hostname,
		"type":      "offline",
		"timestamp": time.Now().Unix(),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("JSON marshal failed: %w", err)
	}
	resp, err := r.client.Post(r.serverURL+"/report", "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("offline report failed: %w", err)
	}
	defer resp.Body.Close()
	log.Printf("Offline report done")
	return nil
}
