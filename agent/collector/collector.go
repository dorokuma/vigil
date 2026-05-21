package collector

// ReportData 一次上报的完整数据
type ReportData struct {
	CPU     CPUStat    `json:"cpu"`
	Memory  MemoryStat `json:"memory"`
	Disks   []DiskStat `json:"disks"`
	Network []NetStat  `json:"network"`
	System  SystemStat `json:"system"`
}

// Collector 采集器
type Collector struct{}

// New 创建采集器
func New() *Collector {
	return &Collector{}
}

// Collect 执行一次采集，返回完整数据
func (c *Collector) Collect() ReportData {
	return ReportData{
		CPU:     GetCPUStat(),
		Memory:  GetMemoryStat(),
		Disks:   GetDiskStats(),
		Network: GetNetworkStats(),
		System:  GetSystemStat(),
	}
}
