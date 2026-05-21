package collector

import (
	"bufio"
	"os"
	"strconv"
	"strings"
	"time"
)

// CPUStat CPU 统计数据
type CPUStat struct {
	Percent float64 `json:"percent"`
	Load1   float64 `json:"load_1"`
	Load5   float64 `json:"load_5"`
	Load15  float64 `json:"load_15"`
}

var prevIdle, prevTotal uint64
var prevTime time.Time

func GetCPUStat() CPUStat {
	var stat CPUStat

	data, err := os.ReadFile("/proc/loadavg")
	if err == nil {
		parts := strings.Fields(string(data))
		if len(parts) >= 3 {
			stat.Load1, _ = strconv.ParseFloat(parts[0], 64)
			stat.Load5, _ = strconv.ParseFloat(parts[1], 64)
			stat.Load15, _ = strconv.ParseFloat(parts[2], 64)
		}
	}

	f, err := os.Open("/proc/stat")
	if err != nil {
		return stat
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "cpu ") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 8 {
			break
		}
		var vals [8]uint64
		for i := 0; i < 8; i++ {
			vals[i], _ = strconv.ParseUint(fields[i+1], 10, 64)
		}
		idle := vals[3]
		total := vals[0] + vals[1] + vals[2] + vals[3] + vals[4] + vals[5] + vals[6] + vals[7]

		if prevTotal == 0 {
			prevIdle = idle
			prevTotal = total
			prevTime = time.Now()
			return stat
		}

		deltaIdle := idle - prevIdle
		deltaTotal := total - prevTotal
		if deltaTotal > 0 {
			stat.Percent = float64(deltaTotal-deltaIdle) / float64(deltaTotal) * 100.0
		}
		prevIdle = idle
		prevTotal = total
		prevTime = time.Now()
		break
	}
	return stat
}
