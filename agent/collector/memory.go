package collector

import (
	"os"
	"strconv"
	"strings"
)

type MemoryStat struct {
	Total     uint64  `json:"total_mb"`
	Used      uint64  `json:"used_mb"`
	Available uint64  `json:"avail_mb"`
	Percent   float64 `json:"percent"`
}

func GetMemoryStat() MemoryStat {
	var stat MemoryStat
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return stat
	}
	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		value, _ := strconv.ParseUint(fields[1], 10, 64)
		valueMB := value / 1024
		switch {
		case strings.HasPrefix(line, "MemTotal:"):
			stat.Total = valueMB
		case strings.HasPrefix(line, "MemAvailable:"):
			stat.Available = valueMB
		}
	}
	if stat.Total > 0 {
		stat.Used = stat.Total - stat.Available
		stat.Percent = float64(stat.Used) / float64(stat.Total) * 100.0
	}
	return stat
}
