package main

import (
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"
	"vigil-agent/collector"
	"vigil-agent/reporter"
)

type Config struct {
	ServerURL string `json:"server_url"`
	Interval  int    `json:"interval"`
	Hostname  string `json:"hostname"`
	Token     string `json:"token"`
}

func main() {
	cfg := loadConfig()
	coll := collector.New()
	rep := reporter.New(cfg.ServerURL, cfg.Hostname, cfg.Token)

	ticker := time.NewTicker(time.Duration(cfg.Interval) * time.Second)
	defer ticker.Stop()

	doReport(coll, rep)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)

	for {
		select {
		case <-ticker.C:
			doReport(coll, rep)
		case <-sigCh:
			log.Println("Shutting down, sending offline report...")
			rep.ReportOffline()
			return
		}
	}
}

func doReport(coll *collector.Collector, rep *reporter.Reporter) {
	data := coll.Collect()
	if err := rep.Report(data); err != nil {
		log.Printf("Report failed: %v", err)
	}
}

func loadConfig() Config {
	cfg := Config{
		ServerURL: "http://localhost:9901",
		Interval:  30,
		Hostname:  "",
		Token:     "",
	}
	data, err := os.ReadFile("/etc/vigil/config.json")
	if err != nil {
		log.Printf("No config file found at /etc/vigil/config.json, using defaults")
		return cfg
	}
	if err := json.Unmarshal(data, &cfg); err != nil {
		log.Printf("Config parse error: %v, using defaults", err)
	}
	if cfg.Interval < 10 {
		cfg.Interval = 30
		log.Printf("Interval too small (<10), reset to 30s")
	}
	if cfg.Hostname == "" {
		hostname, err := os.Hostname()
		if err != nil {
			hostname = "unknown"
		}
		cfg.Hostname = hostname
	}
	return cfg
}
