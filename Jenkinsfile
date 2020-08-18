@Library('ciJenkinsLibrary') _

def environ_tag = [develop:"dev", staging:"local",master:"prod"]
def helm_ops = [develop:"ops",staging:"kube-system", master:"ops"]
  
//Library methods don't load noncps tags, so lambda defined here. It allows to non serialize the functions methods that some libraries provide, ie, HashTables...
@NonCPS
def  getUserMail = findUserMail

pipeline {

  agent any

  options { 
	disableConcurrentBuilds() 
  }

  environment { 
    ROOT = "/opt/jenkins"
    DEFAULT_BRANCH_TARGET = "develop"
    DOCKERFILE = "Dockerfile:main"
    REGISTRY = "195146996125.dkr.ecr.eu-central-1.amazonaws.com/"
    IMAGE = "records" 
    HELM_CHART="mog/records-consumer"
    HELM_NSPACE="biomed"
  }
  
  
  parameters {
      string(defaultValue: "0" , description: 'Pipeline starting step', name: 'Step')
      string(defaultValue: "develop" , description: 'Origin branch', name: 'PULL_REQUEST_FROM_BRANCH')
      string(defaultValue: "develop" , description: 'Destination branch', name: 'PULL_REQUEST_TO_BRANCH')
      choice(choices: "OPEN\nMERGED" , description: 'Pull request status', name: 'PULL_REQUEST_STATE')
      string(defaultValue: "vers-0.0.0", description: "Version to deploy ", name: 'DEPLOYMENT_VERSION')
      string(defaultValue: "meysam.zamani@madeofgenes.com", description: "Mail to send notifications ", name: 'MAIL')

  }
 
  stages {
    stage('Setup environment'){
        steps {
            echo "Set branch variables for each environment"
            script {
               if ( !params.MAIL.contains("@")) {
                        ldapMail = sh ( script: "git --no-pager show -s --format=%ae", returnStdout: true).trim()
                        addOrReplaceParamValue("MAIL",ldapMail)
                }
                if ("${params.PULL_REQUEST_STATE}" != "MERGED") {
                        commitId = sh ( script:"git rev-parse remotes/origin/${params.PULL_REQUEST_FROM_BRANCH}", returnStdout: true).trim()
                } else {
                        commitId = sh ( script:"git rev-parse remotes/origin/${params.PULL_REQUEST_TO_BRANCH}", returnStdout: true).trim()
                }
                REPOSITORY = sh ( script: "basename `git rev-parse --show-toplevel` | sed 's/_.*\$//' ",returnStdout: true).trim()
                bitbucketStatusNotify(buildState: 'INPROGRESS', buildKey: "${params.PULL_REQUEST_FROM_BRANCH}-${BUILD_ID}", buildName: "Jenkins job: num ${BUILD_ID}",repoSlug: "${REPOSITORY}", commitId: "${commitId}")
		
		        VERSION = sh(script: "bash -c \"python3 setup.py --version\"", returnStatus: true)
                HELM_NAME = "rabbit-consumer-records"
                CONTEXT_BUILD = environ_tag ["${PULL_REQUEST_TO_BRANCH}"]
                OPS_NSPACE = helm_ops ["${PULL_REQUEST_TO_BRANCH}"]
		        if (!params.ROLLBACK && params.Step.toInteger() <= '5'.toInteger()) {
	                addOrReplaceParamValue("DEPLOYMENT_VERSION",("vers-" + "${VERSION}" + "-${CONTEXT_BUILD}$BUILD_ID"))
		        }
                secrets = [[$class: 'VaultSecret', path: 'services/rabbitmq', secretValues:[
                    [$class: 'VaultSecretValue', envVar: 'rabbit_passwd', vaultKey: "rabbit_passwd_${CONTEXT_BUILD}"]]],
                    [$class: 'VaultSecret', path: 'services/elk-stack', secretValues:[
                    [$class: 'VaultSecretValue', envVar: 'elk_passwd', vaultKey: "elk_passwd"]]]]
                kconfig = [[$class: 'VaultSecret', path: 'services/K8S', secretValues:[
                    [$class: 'VaultSecretValue', envVar: 'config', vaultKey: "kube_${CONTEXT_BUILD}"]]]]
            }
        }

        steps {
                echo "Running tests"
                    script {
                        wrap([$class: 'VaultBuildWrapper', configuration: [vaultCredentialId: 'vault-jenkins', vaultUrl: 'https://vault.genomcore.net:8200'], vaultSecrets: secrets]) {
                            docker.image("postgres:9.6.3-alpine").withRun("-e POSTGRES_DB=healthcaredb_test -e POSTGRES_PASSWORD=\"postgres\" -e POSTGRES_USER=postgres -p ${PORT}:5432 --name apitest$env.BRANCH_NAME"){ c ->
                                sh """#!/bin/bash -ex
                                    echo "Setting test parameters"
                                    sed -i "s#__rabbit_passwd__#$env.rabbit_passwd#g" config.py     
                                    sed -i "s#__elk_passwd__#$env.elk_passwd#g" config.py     

                                    echo "Starting test"
                                    export NODE_ENV=test
                                    npm run $TEST_PARAMS
                                """
                            }
                        }
                    } 
                }
    }
      stage("Build") {
          when {
                expression{
                    params.PULL_REQUEST_STATE != 'MERGED' && !params.ROLLBACK
                }
            }
             steps {
                checkout ( [
                    $class: 'GitSCM',
                    branches: [[name: "${params.PULL_REQUEST_FROM_BRANCH}"]],
                    doGenerateSubmoduleConfigurations: false,
                    userRemoteConfigs: scm.userRemoteConfigs,
                    extensions: [[
                        $class: 'PreBuildMerge',
                        options: [      
                                fastForwardMode: 'NO_FF',
                                mergeRemote: 'origin',
                                mergeTarget: "${params.PULL_REQUEST_TO_BRANCH}"
                                ]       
                    ],                          
                    [                   
                        $class: 'LocalBranch',  
                        localBranch: "${params.PULL_REQUEST_TO_BRANCH}"
                    ],          
                    [
                        $class: 'CleanBeforeCheckout'
                    ],
                    [   
                        $class: 'WipeWorkspace'
                    ],
                    [
                        $class: 'SubmoduleOption',
                        disableSubmodules: false,
                        parentCredentials: true,
                        recursiveSubmodules: true,
                        reference: '',
                        trackingSubmodules: true
                    ]
                ]

                ])

		 echo "Setting python environment"
		 sshagent (credentials: ['jenkins-deployment-ssh-keys']) {
	                 sh  """#!/bin/bash -xe
				#virtualenv -p python3 env
				#. env/bin/activate
				#pip3  install -r requirements.txt
		     	"""
		 }
      "
      "
      "
    stage('Test') {
        when{
            expression {
                params.PULL_REQUEST_STATE != 'MERGED' && params.Step.toInteger() <= '1'.toInteger() && !params.ROLLBACK
            }
        }
        steps {
	    echo "Running tests"
            sh """#!/bin/bash -xe
		  #. env/bin/activate
		  #export PYTHONPATH=\$PYTHONPATH:\$PWD
		  #py.test --junitxml=unittests.xml --cov-report html --cov taskworker --verbose
	       """
        }
        post {
            always {
                junit '*.xml'
                publishHTML([allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true, reportDir: 'htmlcov/', reportFiles: 'index.html', reportName: 'Coverage report', reportTitles: ''])
            }
        }
    }
    
    stage('QA'){
        when{
            expression {
                params.PULL_REQUEST_STATE != 'MERGED' && params.Step.toInteger() <= '2'.toInteger() && !params.ROLLBACK
            }
        }
        steps {
            echo "checkstyle plugin"
	    warnings( canComputeNew: false, canResolveRelativePaths: false, categoriesPattern: '', consoleParsers: [[parserName: 'PyLint']], defaultEncoding: '', excludePattern: '', healthy: '', includePattern: '', messagesPattern: '', parserConfigurations: [[parserName: 'PyLint', pattern: '.*.py']], unHealthy: '')
	    echo "Generating docs"
	    sh """#!/bin/bash -xe
          #. env/bin/activate
		  #./bin/create_documentation.sh
	       """
            
            script {
                echo "PR job done. Exiting....."
                addOrReplaceParamValue("Step","10")
             }
        }
    }
   
    stage('Bake'){
        when{
            expression {
                params.PULL_REQUEST_STATE == 'MERGED'  && params.Step.toInteger() <= '3'.toInteger() && !params.ROLLBACK
            }
        }
        steps {
            echo "Build docker image"
            script {
	                docker.build("$REGISTRY$IMAGE:iuconsumer-${params.DEPLOYMENT_VERSION}", "-f Dockerfile-consumer  .")
                    docker.build("$REGISTRY$IMAGE:dconsumer-${params.DEPLOYMENT_VERSION}", "-f Dockerfile-consumer-d  .")
			        
		}
        }
    }

    stage('Store'){
        when{
            expression {
                params.PULL_REQUEST_STATE == 'MERGED' && params.Step.toInteger() <= '4'.toInteger() && !params.ROLLBACK
            }
        }
        steps {
            echo "Storing docker images"
            script {
                docker.withRegistry("https://$REGISTRY$IMAGE","ecr:eu-central-1:AWS-ACCES"){
                    def imageiu = docker.image("$REGISTRY$IMAGE:iuconsumer-${params.DEPLOYMENT_VERSION}")
                    def imaged = docker.image("$REGISTRY$IMAGE:dconsumer-${params.DEPLOYMENT_VERSION}")
                    imageiu.push()
                    imaged.push()
                }
                
            }
        }
    }

    stage('Deploy'){
        when{
            expression {
                params.PULL_REQUEST_STATE == 'MERGED' && params.Step.toInteger() <= '6'.toInteger() && !params.ROLLBACK
            }
        }
        steps {
            echo "Deploy new docker version"
            wrap([$class: 'VaultBuildWrapper', configuration: [vaultCredentialId: 'vault-jenkins', vaultUrl: 'https://vault.genomcore.net:8200'], vaultSecrets: kconfig]) {
                    sh """#!/bin/bash -xe 
                    cat <<<  "$env.config" > config
                    kubectl get nodes --kubeconfig config
	               	helm upgrade --kubeconfig config --install $HELM_NAME $HELM_CHART --namespace $HELM_NSPACE --tiller-namespace ${OPS_NSPACE} --set image.tag=${params.DEPLOYMENT_VERSION},replicaCount=1 --debug
                    """
                }
           }
    }

    stage('Rollback'){
        when{
            expression {
                params.ROLLBACK 
            }
        }
        steps {
            echo "Rollback to version: ${params.DEPLOYMENT_VERSION} "
            withCredentials([file(credentialsId: 'kube-${CONTEXT_BUILD}-file', variable: 'config')]) {
                sh 'cat $config > $HOME/.kube/config'
            } 
            sh "helm upgrade --install $HELM_NAME $HELM_CHART --namespace $HELM_NSPACE --set image.tag=${params.DEPLOYMENT_VERSION},replicaCount=1,args[1]=${params.WORKER_CLASS},app.name=${params.WORKER_CLASS} --debug"
            sh 'rm $HOME/.kube/config'
            
        }
    }

    }
    post {
        success {
                bitbucketStatusNotify(buildState: 'SUCCESSFUL', buildKey: "${params.PULL_REQUEST_FROM_BRANCH}-${BUILD_ID}", buildName: "Jenkins job: num ${BUILD_ID}",repoSlug: "${REPOSITORY}", commitId: "${commitId}")
        }
	failure{
		emailext(subject:"Failure build num. $BUILD_ID for job $JOB_NAME", body:"$BUILD_URL", to: "$MAIL")
                bitbucketStatusNotify(buildState: 'FAILURE', buildKey: "${params.PULL_REQUEST_FROM_BRANCH}-${BUILD_ID}", buildName: "Jenkins job: num ${BUILD_ID}",repoSlug: "${REPOSITORY}", commitId: "${commitId}")
	}
    }
}

