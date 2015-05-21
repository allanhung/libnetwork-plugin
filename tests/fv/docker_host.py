import sh
from sh import docker


class DockerHost(object):
    """
    A host container which will hold workload containers to be networked by calico.
    """
    def __init__(self, name):
        self.name = name

        pwd = sh.pwd().stdout.rstrip()
        docker.run("--privileged", "-v", pwd+":/code", "--name", self.name, "-tid", "jpetazzo/dind")
        print "Host container created"

        # Load the saved images into the host containers.
        self.execute("while ! docker ps; do sleep 1; done && "
                   "docker load --input /code/calico-node.tar && "
                   "docker load --input /code/busybox.tar && "
                   "docker load --input /code/nsenter.tar")

    def execute(self, command):
        return docker("exec", "-t", self.name, "bash", c=command)

    def start_etcd(self):
        # Set up the single-node etcd cluster inside host1.
        self.execute("docker load --input /code/etcd.tar")

        host_ip = docker.inspect("--format", "'{{ .NetworkSettings.IPAddress }}'", self.name).stdout.rstrip()
        cmd = ("--name calico "
               "--advertise-client-urls http://%s:2379 "
               "--listen-client-urls http://0.0.0.0:2379 "
               "--initial-advertise-peer-urls http://%s:2380 "
               "--listen-peer-urls http://0.0.0.0:2380 "
               "--initial-cluster-token etcd-cluster-2 "
               "--initial-cluster calico=http://%s:2380 "
               "--initial-cluster-state new" % (host_ip, host_ip, host_ip))
        self.execute("docker run -d -p 2379:2379 quay.io/coreos/etcd:v2.0.10 %s" % cmd)
        print "Etcd container started"
