package collector

import (
	"bufio"
	"os"
	"strconv"
	"strings"
	"time"
)

type NetStat struct {
	Interface string `json:"interface"`
	RxBytes   uint64 `json:"rx_bytes"`
	TxBytes   uint64 `json:"tx_bytes"`
	RxSpeed   uint64 `json:"rx_speed_bps"`
	TxSpeed   uint64 `json:"tx_speed_bps"`
}

type netSample struct {
	rxBytes, txBytes uint64
	time             time.Time
}


func (c *Collector) GetNetworkStats() []NetStat {
	var stats []NetStat
	f, err := os.Open("/proc/net/dev")
	if err != nil {
		return stats
	}
	defer f.Close()

	now := time.Now()
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, "Inter-|") || strings.Contains(line, " face ") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 10 {
			continue
		}
		iface := strings.TrimRight(fields[0], ":")
		if iface == "lo" {
			continue
		}
		rxBytes, _ := strconv.ParseUint(fields[1], 10, 64)
		txBytes, _ := strconv.ParseUint(fields[9], 10, 64)

		stat := NetStat{Interface: iface, RxBytes: rxBytes, TxBytes: txBytes}
		if prev, ok := c.netPrev[iface]; ok {
			elapsed := now.Sub(prev.time).Seconds()
			if elapsed > 0 {
				stat.RxSpeed = uint64(float64(rxBytes-prev.rxBytes) / elapsed)
				stat.TxSpeed = uint64(float64(txBytes-prev.txBytes) / elapsed)
			}
		}
		stats = append(stats, stat)
		c.netPrev[iface] = netSample{rxBytes: rxBytes, txBytes: txBytes, time: now}
	}
	return stats
}
