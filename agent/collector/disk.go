package collector

import "syscall"

type DiskStat struct {
	MountPoint string  `json:"mount_point"`
	Total      uint64  `json:"total_gb"`
	Used       uint64  `json:"used_gb"`
	Free       uint64  `json:"free_gb"`
	Percent    float64 `json:"percent"`
}

func GetDiskStats() []DiskStat {
	var stats []DiskStat
	mounts := []string{"/", "/var/lib/docker", "/root"}
	for _, mount := range mounts {
		var stat syscall.Statfs_t
		if err := syscall.Statfs(mount, &stat); err != nil {
			continue
		}
		total := stat.Blocks * uint64(stat.Bsize) / (1024 * 1024 * 1024)
		free := stat.Bavail * uint64(stat.Bsize) / (1024 * 1024 * 1024)
		used := total - free
		var percent float64
		if total > 0 {
			percent = float64(used) / float64(total) * 100.0
		}
		stats = append(stats, DiskStat{
			MountPoint: mount, Total: total, Used: used,
			Free: free, Percent: percent,
		})
	}
	return stats
}
