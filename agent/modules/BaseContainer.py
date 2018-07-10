import os, io, sys, time, datetime, shutil, logging

import docker

logger = logging.getLogger(__name__)


WHALER_DATA_OUTPUT_FOLDER="/tmp/whaler/"

class BaseContainer:
	
	def __init__(self, cliUrl, containerName):
		self.cli = self.getCli(cliUrl)
		self.containerName=containerName
		self.container=self.getContainer()
		self.baselineChangedFiles = []

	def deployContainer(self):
		self.container=self.getContainer()

	def captureEvidence(self):
		pass

	def getCli(self, url):
		return docker.DockerClient(base_url=url)

	def getContainer(self, containerName=None):
		if not containerName: 
			containerName = self.containerName
		try:
			logger.info("Getting container %s " % containerName)
			return self.cli.containers.get(containerName)
		except Exception as e:
			logger.warn("unable to get container [%s] error[%s]" % (containerName, e))	
			return None

	def stopContainer(self, targetContainer=None):
		if targetContainer: 
			container=targetContainer
		else:
			container=self.container

		if container:
			logger.info("Stopping container %s" % container.name)
			container.stop()
			logger.info("Stopped container %s" % container.name)
		else:
			logger.warn("Could not stop container, has it been initialised?")

	def removeContainer(self):
		if not self.container:
			logger.warn("Could not remove container, has it been initialised?")
			return

		try:
			logger.info("Removing container [%s]" % self.containerName)
			self.container.remove(force=True)
			self.container=None
			logger.info("removed cotaniner [%s]" % self.containerName)
		except docker.errors.NotFound:
			logger.warn("container [%s] not found to remove" % self.containerName)
		except Exception as e:
			logger.error("Unable to kill / remove container [%s]" % e)
	

	def redeployContainer(self):
		self.removeContainer()
		self.deployContainer()

	def snapshotContainer(self, container, filePath):
		logger.info("Snapshotting image and container for [%s] to [%s]" % (container.name, filePath))

		if not os.path.exists(filePath): os.makedirs(filePath)
		try:
			logger.info("container %s" % container)
			logger.info("tags %s" % container.labels)
			logger.info("image %s" % container.image)

		except Exception as e:
			logger.info(e)

		image=container.image
		outputFile=filePath + '/IMG_' + container.name + '-' + container.id + '.tar'
		f = open(outputFile, 'w')

		for chunk in image.save():
			f.write(chunk)
		f.close()
		logger.info("{'timestamp':'%s', source':'ContainerManager', 'action':'SavedContainerImage', 'containerId':'%s', 'imageId':'%s', 'file':'%s'}" % (datetime.datetime.now().isoformat(),container.id,image.tags,outputFile))

		outputFile=filePath + '/CNT_' + container.name + '-' + container.id + '.tar'
		f = open(outputFile, 'w')

		for chunk in container.export():
			f.write(chunk)
		f.close()
		logger.info("{'timestamp':'%s', source':'ContainerManager', 'action':'SavedContainer', 'containerId':'%s', 'imageId':'%s', 'file':'%s'}" % (datetime.datetime.now().isoformat(),container.id,image.tags,outputFile))
	
	def resetBaselineFileChanges(self):
		self.baselineChangedFiles = self.getAllFileSystemChanges()
		
	def getAllFileSystemChanges(self):
		if not self.container:
			logger.warn("Could not baseline changed files for container [%s], has container been initialised?" % self.containerName)
			return
	
		result=[]
		for diff in self.container.diff():
			result.append(diff['Path'])
		return result
	
	def getFileSystemDifferencesFromBaseline(self):
		diffs = self.getAllFileSystemChanges()
			
		newFiles=[]
		for diff in diffs:
			if diff not in self.baselineChangedFiles and not diff.startswith("/run/docker/"):
				newFiles.append(diff)
		
		return newFiles