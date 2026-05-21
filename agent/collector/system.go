package collector

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type SystemStat struct {
	Hostname   string `json:"hostname"`
	UptimeSec  uint64 `json:"uptime_sec"`
	ProcessCnt int    `json:"process_cnt"`
	KernelVer  string `json:"kernel_version"`
	Timestamp  int64  `json:"timestamp"`
}

func GetSystemStat() SystemStat {
	var stat SystemStat
	stat.Timestamp = time.Now().Unix()

	hostname, err := os.Hostname()
	if err == nil {
		stat.Hostname = hostname
	}

	data, err := os.ReadFile("/proc/uptime")
	if err == nil {
		parts := strings.Fields(string(data))
		if len(parts) > 0 {
			sec, _ := strconv.ParseFloat(parts[0], 64)
			stat.UptimeSec = uint64(sec)
		}
	}

	f, err := os.Open("/proc")
	if err == nil {
		entries, _ := f.Readdir(-1)
		f.Close()
		for _, e := range entries {
			if e.IsDir() {
				name := e.Name()
				isNum := true
				for _, c := range name {
					if c < '0' || c > '9' {
						isNum = false
						break
					}
				}
				if isNum {
					stat.ProcessCnt++
				}
			}
		}
	}

	data, err = os.ReadFile("/proc/version")
	if err == nil {
		stat.KernelVer = strings.TrimSpace(string(data))
	}
	return stat
}
