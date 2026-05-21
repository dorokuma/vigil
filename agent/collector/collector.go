package collector

import "time"

// ReportData 一次上报的完整数据
type ReportData struct {
	CPU     CPUStat    `json:"cpu"`
	Memory  MemoryStat `json:"memory"`
	Disks   []DiskStat `json:"disks"`
	Network []NetStat  `json:"network"`
	System  SystemStat `json:"system"`
}

// Collector 采集器
type Collector struct {
	cpuPrevIdle  uint64
	cpuPrevTotal uint64
	cpuPrevTime  time.Time
	netPrev      map[string]netSample
}

// New 创建采集器
func New() *Collector {
	return &Collector{
		netPrev: make(map[string]netSample),
	}
}

// Collect 执行一次采集，返回完整数据
func (c *Collector) Collect() ReportData {
	return ReportData{
		CPU:     c.GetCPUStat(),
		Memory:  GetMemoryStat(),
		Disks:   GetDiskStats(),
		Network: c.GetNetworkStats(),
		System:  GetSystemStat(),
	}
}
