import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('compute1', username='root', password='openstack')

#stdin, stdout, stderr = client.exec_command('service detectionagent stop')
stdin, stdout, stderr = client.exec_command('service detectionagent restart')
print (stdout.read())
